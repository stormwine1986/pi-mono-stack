---
name: "browser-use"
description: "Automates browser interactions for web testing, form filling, and screenshots. Use when the user needs to navigate websites, interact with web pages, fill forms, or take screenshots."
---

# Browser Automation with `browser-use` CLI

The `browser-use` command provides fast, persistent browser automation running inside a Docker container. It maintains browser sessions across commands, enabling complex multi-step workflows.


### 1. Execute Commands
Run commands directly from your host machine using `docker exec`:

```bash
docker exec browser-use browser-use open https://example.com
```

## Quick Start

```bash
# Navigate to URL
docker exec browser-use browser-use open https://example.com

# Get page elements with indices
docker exec browser-use browser-use state

# Click element by index (e.g., index 5)
docker exec browser-use browser-use click 5

# Type text
docker exec browser-use browser-use type "Hello World"

# Take screenshot
docker exec browser-use browser-use screenshot

# Close browser
docker exec browser-use browser-use close
```

## Core Workflow

1. **Navigate**: `browser-use open <url>` - Opens URL (starts browser if needed)
2. **Inspect**: `browser-use state` - Returns clickable elements with indices
3. **Interact**: Use indices from state to interact (`browser-use click 5`, `browser-use input 3 "text"`)
4. **Verify**: `browser-use state` or `browser-use screenshot` to confirm actions
5. **Repeat**: Browser stays open between commands

## Commands

### Navigation
```bash
docker exec browser-use browser-use open <url>                    # Navigate to URL
docker exec browser-use browser-use back                          # Go back in history
docker exec browser-use browser-use scroll down                   # Scroll down
docker exec browser-use browser-use scroll up                     # Scroll up
```

### Page State
```bash
docker exec browser-use browser-use state                         # Get URL, title, and clickable elements
docker exec browser-use browser-use screenshot                    # Take screenshot (outputs base64)
docker exec browser-use browser-use screenshot .browser-use/path.png           # Save screenshot to file
docker exec browser-use browser-use screenshot --full .browser-use/path.png    # Full page screenshot
```

### Interactions (use indices from `browser-use state`)
```bash
docker exec browser-use browser-use click <index>                 # Click element
docker exec browser-use browser-use type "text"                   # Type text into focused element
docker exec browser-use browser-use input <index> "text"          # Click element, then type text
docker exec browser-use browser-use keys "Enter"                  # Send keyboard keys
docker exec browser-use browser-use keys "Control+a"              # Send key combination
docker exec browser-use browser-use select <index> "option"       # Select dropdown option
```

### Tab Management
```bash
docker exec browser-use browser-use switch <tab>                  # Switch to tab by index
docker exec browser-use browser-use close-tab                     # Close current tab
docker exec browser-use browser-use close-tab <tab>               # Close specific tab
```

### JavaScript
```bash
docker exec browser-use browser-use eval "document.title"         # Execute JavaScript, return result
```

## Prohibited Commands

- **DO NOT USE** `browser-use extract`. This command is strictly prohibited as it triggers internal LLM calls that are not compatible with the current environment. For data extraction, use `browser-use state` and `browser-use eval` to manually inspect and retrieve required information.

### Session Management
```bash
docker exec browser-use browser-use sessions                      # List active sessions
docker exec browser-use browser-use close                         # Close current session
docker exec browser-use browser-use close --all                   # Close all sessions
```

## Examples

### Form Submission
```bash
docker exec browser-use browser-use open https://example.com/contact
docker exec browser-use browser-use state
# Shows: [0] input "Name", [1] input "Email", [2] textarea "Message", [3] button "Submit"
docker exec browser-use browser-use input 0 "John Doe"
docker exec browser-use browser-use input 1 "john@example.com"
docker exec browser-use browser-use input 2 "Hello, this is a test message."
docker exec browser-use browser-use click 3
docker exec browser-use browser-use state  # Verify success
```

## Tips

1. **Always run `docker exec browser-use browser-use state` first** to see available elements and their indices
2. **Sessions persist** - the browser stays open between commands
3. **Use `--json` for parsing** output programmatically
4. **Screenshots** - Files should be saved to the `.browser-use` directory to keep the workspace clean. Example: `docker exec browser-use browser-use screenshot .browser-use/page.png`.

## Cleanup

**Always close the browser when done.** Run this after completing browser automation:

```bash
docker exec browser-use browser-use close
```
