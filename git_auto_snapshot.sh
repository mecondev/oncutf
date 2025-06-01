#!/bin/bash

# === [Paths] ===
PROJECT_DIR="/mnt/data_1/edu/Python/oncutf"
LOG_FILE="$PROJECT_DIR/git_cron.log"

# === [Activate pyenv manually for cron] ===
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"

# Optional: Force version (not strictly needed if already global)
export PYENV_VERSION="3.13.0"

# === [Go to project dir] ===
cd "$PROJECT_DIR" || {
    echo "[ERROR] Project dir not found: $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# === [Snapshot process] ===
echo "[INFO] Snapshot started at $(date)" >> "$LOG_FILE"

git add -A

if ! git diff --cached --quiet; then
    git commit -m "Auto snapshot at $(date '+%Y-%m-%d %H:%M')" >> "$LOG_FILE" 2>&1
    echo "[INFO] Commit created" >> "$LOG_FILE"
else
    echo "[INFO] No changes to commit" >> "$LOG_FILE"
fi
