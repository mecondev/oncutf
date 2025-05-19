#!/bin/bash

echo "🧹 Cleaning temporary files and folders..."

# Test & coverage
rm -rf .pytest_cache .coverage htmlcov/

# Build artifacts
rm -rf build/ dist/ *.egg-info/

# Python cache
find . -type d -name '__pycache__' -exec rm -rf {} +
find . -type f -name '*.py[co]' -delete

# Virtual envs & misc
rm -rf v/ env/ venv/

# IDEs
rm -rf .vscode/ .idea/

# Logs & reports
rm -f *.log docstrings_report.txt

# Old ignored structure
rm -f reports/structure.md

echo "✅ Project cleaned!"
