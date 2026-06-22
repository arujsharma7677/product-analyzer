#!/usr/bin/env bash
#
# Push variables from a local .env file into your deployment platform so the
# app picks them up as real environment variables when deployed.
#
# Usage:
#   ./scripts/push-env.sh railway            # push to the linked Railway service
#   ./scripts/push-env.sh render <service-id>  # push to a Render service
#   ./scripts/push-env.sh railway path/to/.env
#
# Prerequisites:
#   Railway -> npm i -g @railway/cli, then `railway login` and `railway link`
#   Render  -> set RENDER_API_KEY (https://dashboard.render.com/u/settings#api-keys)
#
set -euo pipefail

PLATFORM="${1:-}"

if [[ "$PLATFORM" != "railway" && "$PLATFORM" != "render" ]]; then
  echo "Usage: $0 <railway|render> [args]" >&2
  exit 1
fi

# Resolve the .env file (last arg for railway, 3rd arg for render).
if [[ "$PLATFORM" == "render" ]]; then
  SERVICE_ID="${2:-}"
  ENV_FILE="${3:-.env}"
  if [[ -z "$SERVICE_ID" ]]; then
    echo "Render requires a service id: $0 render <service-id> [.env]" >&2
    exit 1
  fi
else
  ENV_FILE="${2:-.env}"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

# Read KEY=VALUE pairs, skipping blanks and comments. Values may contain '='.
read_env() {
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"                         # strip trailing CR
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" != *=* ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key// /}"                             # trim spaces around key
    printf '%s\t%s\n' "$key" "$value"
  done < "$ENV_FILE"
}

push_railway() {
  command -v railway >/dev/null 2>&1 || { echo "railway CLI not found. npm i -g @railway/cli" >&2; exit 1; }
  local args=()
  while IFS=$'\t' read -r key value; do
    echo "  + $key"
    args+=(--set "$key=$value")
  done < <(read_env)
  railway variables "${args[@]}"
  echo "Pushed env to Railway."
}

push_render() {
  : "${RENDER_API_KEY:?Set RENDER_API_KEY first}"
  command -v jq >/dev/null 2>&1 || { echo "jq is required for Render. brew install jq" >&2; exit 1; }
  # Build a JSON array of {key,value} for the bulk env-vars endpoint.
  local payload="[]"
  while IFS=$'\t' read -r key value; do
    echo "  + $key"
    payload=$(jq -c --arg k "$key" --arg v "$value" '. + [{key:$k,value:$v}]' <<<"$payload")
  done < <(read_env)

  curl -fsS -X PUT \
    "https://api.render.com/v1/services/${SERVICE_ID}/env-vars" \
    -H "Authorization: Bearer ${RENDER_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$payload" >/dev/null
  echo "Pushed env to Render (a new deploy will be triggered)."
}

case "$PLATFORM" in
  railway) push_railway ;;
  render)  push_render ;;
esac
