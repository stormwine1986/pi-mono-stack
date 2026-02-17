# Gateway Module Data Protocol Design

This document outlines the data protocol design for the Gateway module in the Pi Mono Stack.

## Overview

The Gateway module serves as the entry point for external communication, handling message routing and transformation.

## Protocol Specifications

### 1. Agent Input (`agent_in`)
Stream: `agent_in` (Redis Stream)
Direction: Gateway -> Agent

Represents a task or prompt sent to the Agent for processing.

**Format (JSON):**
```json
{
  "id": "uuid-string",       // Unique task identifier
  "source": "string",        // Source of the request (e.g., "telegram", "web")
  "prompt": "string",        // User prompt or command text
  "metadata": { ... }        // Optional metadata
}
```

### 2. Agent Output (`agent_out`)
Stream: `agent_out` (Redis Stream)
Direction: Agent -> Gateway

Represents the response or status update from the Agent.

**Format (JSON):**
```json
{
  "id": "uuid-string",       // Corresponds to the input task ID
  "status": "success" | "error" | "progress",
  "response": "string",      // Final text response (if status is success)
  "error": "string",         // Error message (if status is error)
  "event": "string",         // Progress event type (e.g., "llm_start", "tool_use")
  "data": { ... }            // Additional event data
}
```

### 3. Agent Control (`agent_ctl`)
Channel: `agent_ctl` (Redis PubSub)
Direction: Gateway -> Agent

Control signals to manage the Agent's lifecycle or current operation.

**Format (JSON):**
```json
{
  "id": "uuid-string",       // Optional task ID to target
  "command": "stop" | "steer" | "reset",
  "message": "string"        // Optional message or instruction
}
```

### 4. Dkron Output (`dkron_out`)
Stream: `dkron_out` (Redis Stream)
Direction: Dkron Wrapper -> Agent/Monitor

Stream of job execution results from Dkron tasks.

**Format (JSON):**
```json
{
  "job": "string",           // Job name (e.g., "backup-task")
  "exit_code": number,       // Exit code (0 for success)
  "output": "string",        // Combined stdout and stderr of the command
  "timestamp": "ISO-8601"    // Execution timestamp (UTC)
}
```
