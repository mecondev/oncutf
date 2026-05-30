# Development Guide

## Prerequisites

- Python 3.13+
- Git
- **exopsis** — installed from the project's private repository via
  `requirements.txt` (not on PyPI)

## Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/mecondev/oncutf.git
   cd oncutf
   ```

2. **Install development dependencies**

   ```bash
   make install-dev
   # or
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**

   ```bash
   make install-hooks
   # or
   pre-commit install
   ```

4. **Run the application**

   ```bash
   make run
   # or
   python main.py
   ```

## Command-Line Arguments

```
python main.py [options]
```

| Argument | Description |
| -------- | ----------- |
| `-V`, `--version` | Print version string and exit. |
| `--debug` | Set log level to DEBUG (default is INFO). |
| `--no-splash` | Skip the splash screen on startup (useful during development). |
| `-c`, `--clean` | Delete database and `config.json` on startup (fresh start). |
| `-h`, `--help` | Show help message and exit. |

Qt passes any unrecognised flags through to the Qt platform plugin
(e.g. `-platform xcb`, `-style Fusion`).

### Examples

```bash
python main.py --version          # oncutf 1.3
python main.py --debug            # full debug logging
python main.py --no-splash        # skip splash (faster dev loop)
python main.py --no-splash --debug
python main.py --clean            # fresh start: wipe db + config.json
```

## Development Commands

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Type checking
make type-check

# Run all quality checks
make lint && make format && make type-check
```

### Testing

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Run specific test categories
pytest tests/ -m "not slow"  # Skip slow tests
pytest tests/ -m "unit"      # Only unit tests
pytest tests/ -m "integration"  # Only integration tests
pytest tests/ -m "gui"       # Only GUI tests
pytest tests/ -m "metadata"  # Only tests requiring metadata extraction
```

### Building

```bash
# Clean build artifacts
make clean

# Build package
make build

# Create distribution
make dist
```

## Project Structure

See [CLAUDE.md](CLAUDE.md#architecture) and [docs/architecture.md](docs/architecture.md)
for the authoritative layer breakdown. Top level:

```tree
oncutf/
├── boot/         # Composition root (startup, DI wiring, shutdown)
├── ui/           # PyQt5 widgets, behaviors, delegates, dialogs, Qt models
├── controllers/  # UI-agnostic orchestration
├── app/          # Application services: ports, services, state
├── core/         # Business logic (cache, database, file, hash, metadata, rename)
├── domain/       # Pure data models + rules (no Qt/UI/infra)
├── infra/        # External tools (exopsis, ffmpeg), SQLite, caches, filesystem
├── modules/      # Composable rename-fragment modules
├── config/       # Configuration constants
└── utils/        # Cross-cutting helpers (Qt-free; utils/ui for Qt helpers)
```

## Code Style

This project uses:

- **Ruff** for linting and formatting
- **Black** for code formatting
- **MyPy** for type checking
- **Pre-commit hooks** for automated checks

### Configuration Files

- `pyproject.toml` - Main configuration for all tools
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `Makefile` - Development commands

## Testing

### Test Categories

- **Unit tests** (`@pytest.mark.unit`) - Test individual functions/classes
- **Integration tests** (`@pytest.mark.integration`) - Test component interactions
- **GUI tests** (`@pytest.mark.gui`) - Test PyQt5 UI components
- **Slow tests** (`@pytest.mark.slow`) - Tests that take longer to run
- **Metadata tests** (`@pytest.mark.metadata`) - Tests requiring metadata extraction (exopsis)

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_metadata_manager.py

# Run tests matching pattern
pytest -k "test_metadata"

# Run tests in parallel
pytest -n auto
```

## Debugging

### Logging

The application uses structured logging with `get_cached_logger()`.

#### Logger Initialization

```python
# Default pattern (all layers except domain):
from oncutf.utils.logging.logger_factory import get_cached_logger
logger = get_cached_logger(__name__)
```

**Exception — `domain/` must stay free of `oncutf.utils` imports** (enforced by
`tools/audit_boundaries.py`). Domain modules use stdlib logging instead; the
`dev_only` console filter still applies via the root handlers they propagate to:

```python
# domain/ only:
import logging
logger = logging.getLogger(__name__)
```

#### Log Levels

| Level | Usage |
| ----- | ----- |
| `DEBUG` | Development-only messages, verbose details |
| `INFO` | Operation milestones (file loaded, rename completed) |
| `WARNING` | Recoverable issues (failed to load optional data) |
| `ERROR` | Operation failures that need attention |
| `CRITICAL` | Application-wide failures |

#### Exception Logging

```python
# For unexpected exceptions - include full stack trace:
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed: %s", e)

# For expected/handled exceptions - no stack trace needed:
try:
    optional_operation()
except FileNotFoundError:
    logger.warning("Optional file not found, using defaults")
```

#### Log Message Formatting

```python
# Use %-formatting (NOT f-strings):
logger.info("Processing %d files in %s", count, folder)

# NOT:
# logger.info(f"Processing {count} files")  # Wrong!
```

Set log level in `config.py`:

```python
LOG_LEVEL = "DEBUG"  # For development
```

### PyQt5 Debugging

For PyQt5-specific issues:

```bash
# Enable Qt debug output
export QT_LOGGING_RULES="*.debug=true"
python main.py
```

### Database Debugging

```python
# In oncutf/config/app.py
DEBUG_FRESH_START = True  # Delete + recreate database on startup
```

Or use the CLI flag: `python main.py --clean`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run quality checks: `make lint && make format && make type-check`
5. Run tests: `make test`
6. Commit with a descriptive message
7. Push and create a pull request

### Commit Message Format

type(scope): description

[optional body]

[optional footer]

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite: `make test-cov`
4. Build distribution: `make dist`
5. Create GitHub release
6. Upload to PyPI (if applicable)

## Troubleshooting

### Common Issues

**Metadata extraction not available (exopsis missing):**

```bash
# exopsis is not on PyPI — reinstall from requirements.txt
pip install -r requirements.txt
```

**PyQt5 installation issues:**

```bash
# Try installing with specific version
pip install PyQt5==5.15.11
```

**Pre-commit hooks failing:**

```bash
# Update hooks
pre-commit autoupdate

# Skip hooks for this commit
git commit --no-verify
```

**Test failures:**

```bash
# Clean and reinstall
make clean
make install-dev
make test
```
