#!/bin/bash
# Wrapper that reads Google OAuth credentials from gcloud ADC
# and starts the Google Tasks MCP server.
#
# Prerequisites:
#   1. gcloud CLI installed
#   2. Tasks API enabled in GCP project
#   3. ADC configured: gcloud auth application-default login \
#        --client-id-file=<your-client-secret.json> \
#        --scopes="https://www.googleapis.com/auth/tasks,https://www.googleapis.com/auth/cloud-platform"

ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"

if [ ! -f "$ADC_FILE" ]; then
  echo "Error: No ADC credentials at $ADC_FILE" >&2
  echo "Run: gcloud auth application-default login --client-id-file=<client-secret.json> --scopes='https://www.googleapis.com/auth/tasks,https://www.googleapis.com/auth/cloud-platform'" >&2
  exit 1
fi

export GOOGLE_CLIENT_ID=$(python3 -c "import json; print(json.load(open('$ADC_FILE'))['client_id'])")
export GOOGLE_CLIENT_SECRET=$(python3 -c "import json; print(json.load(open('$ADC_FILE'))['client_secret'])")
export GOOGLE_REFRESH_TOKEN=$(python3 -c "import json; print(json.load(open('$ADC_FILE'))['refresh_token'])")

exec npx -y @brandcast_app/google-tasks-mcp
