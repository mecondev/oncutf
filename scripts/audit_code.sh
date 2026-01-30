#!/bin/bash
# Standard Code Audit Script for Oncutf
# Usage: ./scripts/audit_code.sh

# Exit on error
set -e

echo "Running standard code audit..."

# 1. Run Vulture (Dead Code Analysis)
# Min confidence 80 as per standard
echo "----------------------------------------"
echo "Running Vulture (Dead Code Analysis)..."
if command -v vulture &> /dev/null; then
    vulture oncutf --min-confidence 80
else
    echo "vulture not found. Please install dev dependencies."
fi

# 2. Run Ruff (Linting & Style)
echo "----------------------------------------"
echo "Running Ruff (Linting)..."
if command -v ruff &> /dev/null; then
    ruff check .
else
    echo "ruff not found. Please install dev dependencies."
fi

# 3. Code Audit Complete
echo "----------------------------------------"
echo "Audit complete."
