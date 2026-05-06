#!/bin/sh

set -u

models=$(printf '%s' "${AIMS_LOCAL_MODEL_PULL_LIST:-}" | tr ',' ' ')
optional_models=$(printf '%s' "${AIMS_LOCAL_OPTIONAL_MODEL_PULL_LIST:-}" | tr ',' ' ')
failed=""
failures=0

if [ -z "$models" ]; then
  echo "No Ollama models configured for pull."
  exit 0
fi

for model in $models; do
  echo "Pulling $model"
  if ! ollama pull "$model"; then
    failed="$failed $model"
    failures=$((failures + 1))
  fi
done

if [ "$failures" -gt 0 ]; then
  echo "Failed to pull:$failed"
  exit 1
fi

for model in $optional_models; do
  [ -n "$model" ] || continue
  echo "Pulling optional model $model"
  if ! ollama pull "$model"; then
    echo "Optional model pull skipped after failure: $model"
  fi
done
