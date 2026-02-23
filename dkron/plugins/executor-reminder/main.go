package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"time"

	typesv1 "github.com/distribworks/dkron/v4/gen/proto/types/v1"
	"github.com/distribworks/dkron/v4/plugin"
	hashicorp_plugin "github.com/hashicorp/go-plugin"
	"github.com/redis/go-redis/v9"
)

type ReminderExecutor struct{}

func pushToReminderStream(jobName string, message string) {
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://127.0.0.1:6379"
	}

	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Printf("Reminder executor: failed to parse REDIS_URL: %v", err)
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
		"message":   message,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}

	jsonBytes, _ := json.Marshal(payload)

	xAddArgs := &redis.XAddArgs{
		Stream: "reminder_out",
		Values: map[string]interface{}{
			"payload": string(jsonBytes),
		},
	}

	if err := rdb.XAdd(ctx, xAddArgs).Err(); err != nil {
		log.Printf("Reminder executor: failed to push to redis stream: %v", err)
	} else {
		log.Printf("Reminder executor: pushed reminder event to reminder_out for job %s", jobName)
	}
}

func (e *ReminderExecutor) Execute(req *typesv1.ExecuteRequest, cb plugin.StatusHelper) (*typesv1.ExecuteResponse, error) {
	config := req.GetConfig()
	message, ok := config["message"]
	if !ok || message == "" {
		message = "Timer triggered"
	}

	envStr := config["env"]
	if envStr != "" {
		var envs []string
		if err := json.Unmarshal([]byte(envStr), &envs); err == nil {
			for _, envVar := range envs {
				// Each envVar is usually "KEY=VALUE"
				for i := 0; i < len(envVar); i++ {
					if envVar[i] == '=' {
						key := envVar[:i]
						value := envVar[i+1:]
						os.Setenv(key, value)
						break
					}
				}
			}
		} else {
			log.Printf("Reminder executor: failed to parse env: %v", err)
			cb.Update([]byte("Warning: Failed to parse env JSON\n"), true)
		}
	}

	jobName := req.GetJobName()

	log.Printf("Reminder executor: triggering reminder for job %s with message: %s", jobName, message)
	cb.Update([]byte("--- Reminder Triggered ---\n"), false)
	cb.Update([]byte("Message: "+message+"\n"), false)

	pushToReminderStream(jobName, message)

	cb.Update([]byte("--- Reminder Sent ---\n"), false)

	return &typesv1.ExecuteResponse{
		Output: []byte("Reminder sent successfully"),
		Error:  "",
	}, nil
}

func main() {
	hashicorp_plugin.Serve(&hashicorp_plugin.ServeConfig{
		HandshakeConfig: plugin.Handshake,
		Plugins: map[string]hashicorp_plugin.Plugin{
			"executor": &plugin.ExecutorPlugin{
				Executor: &ReminderExecutor{},
			},
		},
		GRPCServer: hashicorp_plugin.DefaultGRPCServer,
	})
}
