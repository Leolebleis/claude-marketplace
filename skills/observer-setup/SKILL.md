---
name: observer-setup
description: "Set up OTEL telemetry export for Claude Code on a new machine. Configures env vars to send data to a Workflow Observer pipeline."
---

# Workflow Observer - OTEL Setup

Sets up Claude Code's OpenTelemetry export on the current machine so sessions are tracked by a Workflow Observer instance.

## Prerequisites

- Workflow Observer stack running somewhere (otel-collector listening on port 4318)
- This machine can reach the collector over the network

## Setup Procedure

### 1. Ask the user for the collector IP/hostname

Prompt: "What's the IP or hostname of your OTEL collector?"

### 2. Detect platform and set env vars

**Windows** (persistent user env vars via `setx`):
```bash
setx CLAUDE_CODE_ENABLE_TELEMETRY 1
setx OTEL_LOGS_EXPORTER otlp
setx OTEL_METRICS_EXPORTER otlp
setx OTEL_EXPORTER_OTLP_PROTOCOL http/protobuf
setx OTEL_EXPORTER_OTLP_ENDPOINT http://<COLLECTOR_IP>:4318
setx OTEL_LOG_TOOL_DETAILS 1
setx OTEL_RESOURCE_ATTRIBUTES host.name=<MACHINE_NAME>
```

**Linux / macOS** (append to `~/.bashrc` or `~/.zshrc`):
```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://<COLLECTOR_IP>:4318
export OTEL_LOG_TOOL_DETAILS=1
export OTEL_RESOURCE_ATTRIBUTES=host.name=$(hostname)
```

Replace `<COLLECTOR_IP>` with the user's answer from step 1. Replace `<MACHINE_NAME>` with a human-readable name for this machine.

### 3. Restart terminal

`setx` and `.bashrc` changes only apply to **new** terminal windows. Tell the user to fully close and reopen their terminal.

### 4. Verify

```bash
echo $OTEL_EXPORTER_OTLP_PROTOCOL
# Should print: http/protobuf
```

## Optional Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OTEL_LOG_USER_PROMPTS` | `0` | Set to `1` to include actual prompt text (sensitive) |
| `OTEL_METRIC_EXPORT_INTERVAL` | `60000` | Metrics flush interval (ms) |
| `OTEL_LOGS_EXPORT_INTERVAL` | `5000` | Logs flush interval (ms) |

## Gotchas

- **`OTEL_EXPORTER_OTLP_PROTOCOL` is required** -- without it, Claude Code silently sends nothing
- **Windows**: `setx` does NOT affect the current terminal, only new ones
- **Linux**: Claude Code doesn't source `.bashrc` in non-login shells -- verify env vars are actually set in the Claude Code process
