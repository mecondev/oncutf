# VSCode Configuration

This directory contains recommended VSCode settings for oncutf development.

## Setup

Copy the files to your `.vscode/` directory (which is gitignored):

```bash
cp .vscode.example/* .vscode/
```

Or create symlinks:

```bash
ln -sf ../.vscode.example/launch.json .vscode/launch.json
ln -sf ../.vscode.example/settings.json .vscode/settings.json
```

## Files

- **launch.json**: Debug configurations for running the app
  - "Run oncutf": Standard launch via `main.py`
  - "Run oncutf (module)": Launch via `python -m oncutf`

- **settings.json**: Python environment and tooling configuration
  - Uses workspace virtual environment (`.venv/`)
  - Enables pytest for testing
  - Configures ruff for linting
  - Sets proper environment variables for GUI applications

## Troubleshooting

If the app closes immediately when using VSCode's Run button:

1. Verify the Python interpreter is set to `.venv/bin/python`
2. Check that `DISPLAY` environment variable is set (Linux)
3. Try running from integrated terminal instead: `python main.py`
4. Use the debugger (F5) to see error messages

## GUI Application Notes

Qt applications require:
- A valid DISPLAY environment (Linux/macOS)
- The terminal to remain open during execution
- Proper event loop handling

The `console: "integratedTerminal"` setting ensures the app runs in VSCode's terminal, keeping it alive during the Qt event loop.
