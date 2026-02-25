package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"time"

	typesv1 "github.com/distribworks/dkron/v4/gen/proto/types/v1"
	"github.com/distribworks/dkron/v4/plugin"
	hashicorp_plugin "github.com/hashicorp/go-plugin"
	"github.com/redis/go-redis/v9"
)

type BackgroundExecutor struct{}

// statusWriter wraps the StatusHelper.Update to implement io.Writer
type statusWriter struct {
	cb    plugin.StatusHelper
	isErr bool
}

func (w *statusWriter) Write(p []byte) (n int, err error) {
	_, err = w.cb.Update(p, w.isErr)
	return len(p), err
}

func pushToRedis(jobName string, exitCode int) {
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://127.0.0.1:6379"
	}

	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Printf("Background executor: failed to parse REDIS_URL: %v", err)
		return
	}

	rdb := redis.NewClient(opts)
	defer rdb.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	owner := os.Getenv("ENV_JOB_OWNER")

	payload := map[string]interface{}{
		"job":       jobName,
		"owner":     owner,
		"exit_code": exitCode,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}

	jsonBytes, _ := json.Marshal(payload)

	xAddArgs := &redis.XAddArgs{
		Stream: "background_out",
		MaxLen: 1000,
		Approx: true,
		Values: map[string]interface{}{
			"payload": string(jsonBytes),
		},
	}

	if err := rdb.XAdd(ctx, xAddArgs).Err(); err != nil {
		log.Printf("Background executor: failed to push to redis stream: %v", err)
	} else {
		log.Printf("Background executor: pushed completion event to background_out for job %s", jobName)
	}
}

func (e *BackgroundExecutor) Execute(req *typesv1.ExecuteRequest, cb plugin.StatusHelper) (*typesv1.ExecuteResponse, error) {
	config := req.GetConfig()
	command, ok := config["command"]
	if !ok || command == "" {
		command = req.GetJobName()
	}

	timeoutStr := config["timeout"]
	envStr := config["env"]

	jobName := req.GetJobName()

	log.Printf("Background executor: starting command %s", command)
	cb.Update([]byte("--- Execution Started ---\n"), false)

	cmd := exec.Command("sh", "-c", command)

	// Set Environment Variables
	cmd.Env = os.Environ()
	if envStr != "" {
		var envs []string
		if err := json.Unmarshal([]byte(envStr), &envs); err == nil {
			cmd.Env = append(cmd.Env, envs...)
		} else {
			log.Printf("Background executor: failed to parse env: %v", err)
			cb.Update([]byte("Warning: Failed to parse env JSON\n"), true)
		}
	}

	// Capture stdout and stderr
	// 1. Send back to Dkron StatusHelper (Streaming)
	// 2. Buffer for the final ExecuteResponse.Output
	// 3. Send to plugin process's stdout/stderr (Dkron agent logs)
	var combinedOutput bytes.Buffer
	stdoutWriter := &statusWriter{cb: cb, isErr: false}
	stderrWriter := &statusWriter{cb: cb, isErr: true}

	cmd.Stdout = io.MultiWriter(os.Stdout, stdoutWriter, &combinedOutput)
	cmd.Stderr = io.MultiWriter(os.Stderr, stderrWriter, &combinedOutput)

	// Handle Timeout
	var timeoutDuration time.Duration
	if timeoutStr != "" {
		var err error
		timeoutDuration, err = time.ParseDuration(timeoutStr)
		if err != nil {
			log.Printf("Background executor: invalid timeout duration %s: %v", timeoutStr, err)
			cb.Update([]byte("Warning: Invalid timeout format, ignoring\n"), true)
		}
	}

	// Start the command
	if err := cmd.Start(); err != nil {
		log.Printf("Background executor: failed to start command: %v", err)
		pushToRedis(jobName, 1)
		return &typesv1.ExecuteResponse{
			Output: []byte("Failed to start: " + err.Error()),
			Error:  "true",
		}, nil
	}

	// Wait logic
	done := make(chan error, 1)
	go func() {
		done <- cmd.Wait()
	}()

	var finalErr bool
	var exitCode int

	if timeoutDuration > 0 {
		select {
		case <-time.After(timeoutDuration):
			log.Printf("Background executor: command %d timed out after %s, killing...", cmd.Process.Pid, timeoutStr)
			cb.Update([]byte("\n--- Execution Timed Out, Killing Process ---\n"), true)
			cmd.Process.Kill()
			finalErr = true
			exitCode = 137
			fmt.Fprintf(&combinedOutput, "\nTimed out after %s", timeoutStr)
		case err := <-done:
			if err != nil {
				finalErr = true
				if exitError, ok := err.(*exec.ExitError); ok {
					exitCode = exitError.ExitCode()
				} else {
					exitCode = 1
				}
			} else {
				finalErr = false
				exitCode = 0
			}
		}
	} else {
		err := <-done
		if err != nil {
			finalErr = true
			if exitError, ok := err.(*exec.ExitError); ok {
				exitCode = exitError.ExitCode()
			} else {
				exitCode = 1
			}
		} else {
			finalErr = false
			exitCode = 0
		}
	}

	cb.Update([]byte("\n--- Execution Finished ---\n"), finalErr)

	// Push completion event to Redis
	pushToRedis(jobName, exitCode)

	errorField := ""
	if finalErr {
		errorField = "error"
		if exitCode != 0 {
			errorField = fmt.Sprintf("exit status %d", exitCode)
		}
	}

	return &typesv1.ExecuteResponse{
		Output: combinedOutput.Bytes(),
		Error:  errorField,
	}, nil
}

func main() {
	hashicorp_plugin.Serve(&hashicorp_plugin.ServeConfig{
		HandshakeConfig: plugin.Handshake,
		Plugins: map[string]hashicorp_plugin.Plugin{
			"executor": &plugin.ExecutorPlugin{
				Executor: &BackgroundExecutor{},
			},
		},
		GRPCServer: hashicorp_plugin.DefaultGRPCServer,
	})
}
