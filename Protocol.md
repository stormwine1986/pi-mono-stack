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
  "id": "string",            // Unique task identifier (nanoId)
  "source": "string",        // Source of the request ("telegram", "dkron")
  "prompt": "string",        // User prompt or command text
  "metadata": {              // Source-specific routing info
    "telegram": "chatId:messageId",   // Present when source is "telegram"
    "dkron": { ... }                  // Present when source is "dkron", contains job execution data
  }
}
```

### 2. Agent Output (`agent_out`)
Stream: `agent_out` (Redis Stream)
Direction: Agent -> Gateway

Represents the response or status update from the Agent.

**Format (JSON):**
```json
{
  "id": "string",            // Corresponds to the input task ID
  "status": "success" | "error" | "progress",
  "response": "string",      // Final text response (if status is success)
  "error": "string",         // Error message (if status is error)
  "event": "llm_start" | "llm_end" | "tool_start" | "tool_end" | "send_media",
  "data": { 
    "path": "string",       // Workspace-relative path to the media file
    "type": "image" | "file" // Type of media
  }            // Additional event data
}
```

### 3. Agent Control (`agent_ctl`)
Channel: `agent_ctl` (Redis PubSub)
Direction: Gateway -> Agent

Control signals to manage the Agent's lifecycle or current operation.

**Format (JSON):**
```json
{
  "id": "string",            // Optional task ID to target
  "command": "stop" | "steer" | "reset",
  "message": "string"        // Optional message or instruction
}
```

### 4. Background Output (`background_out`)
Stream: `background_out` (Redis Stream)
Direction: Dkron -> Gateway

Stream of background task completion events.

`payload` is a json string of message
**Format (JSON):**
```json
{
  "job": "string",           // Job name (e.g., "backup-task")
  "owner": "string",         // Job owner identifier
  "exit_code": number,       // Exit code (0 for success)
  "timestamp": "ISO-8601"    // Execution timestamp (UTC)
}
```

### 5. Reminder Output (`reminder_out`)
Stream: `reminder_out` (Redis Stream)
Direction: Dkron -> Gateway

Stream of reminder triggered events.

`payload` is a json string of message
**Format (JSON):**
```json
{
  "job": "string",           // Job name (e.g., "backup-task")
  "owner": "string",         // Job owner identifier
  "message": "string",       // 提醒的内容
  "timestamp": "ISO-8601"    // Execution timestamp (UTC)
}
```
