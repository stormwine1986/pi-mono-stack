package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Usage: wrapper <command>")
	}

	commandStr := strings.Join(os.Args[1:], " ")

	// Create command execution
	cmd := exec.Command("sh", "-c", commandStr)
	// Capture output
	output, err := cmd.CombinedOutput()

	// Run command and capture exit code
	var exitCode int
	if err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			exitCode = exitError.ExitCode()
		} else {
			fmt.Fprintf(os.Stderr, "Execution failed: %v\n", err)
			exitCode = 1
		}
	} else {
		exitCode = 0
	}

	// Print output to container logs as well
	os.Stdout.Write(output)

	// Push execution result to Redis
	pushToRedis(exitCode, string(output))

	// Propagate exit code
	os.Exit(exitCode)
}

func pushToRedis(exitCode int, output string) {
	// Parse Redis URL
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
        // Default assuming host network or linked service
		redisURL = "redis://127.0.0.1:6379"
	}

	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Printf("Failed to parse REDIS_URL: %v", err)
		return
	}

	rdb := redis.NewClient(opts)
	defer rdb.Close() // Best effort close

	// Context with timeout to avoid hanging
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Metadata from Environment
	jobName := os.Getenv("DKRON_JOB_NAME")
	if jobName == "" {
		jobName = os.Getenv("ENV_JOB_NAME")
	}
	if jobName == "" {
		jobName = "unknown" // Fallback
	}
	description := os.Getenv("ENV_JOB_DESCRIPTION")

	payload := map[string]interface{}{
		"job":         jobName,
		"description": description,
		"exit_code":   exitCode,
		"output":      output,
		"timestamp":   time.Now().UTC().Format(time.RFC3339),
	}

	jsonBytes, _ := json.Marshal(payload)

	// Push to stream 'dkron_out'
	xAddArgs := &redis.XAddArgs{
		Stream: "dkron_out",
		Values: map[string]interface{}{
			"data": string(jsonBytes),
		},
	}

	if err := rdb.XAdd(ctx, xAddArgs).Err(); err != nil {
		log.Printf("Failed to push to redis stream: %v", err)
	}
}
