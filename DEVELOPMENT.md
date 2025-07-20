# Development Guide

## Prerequisites

- Python 3.9+
- ExifTool installed and available in PATH
- Git

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
pytest tests/ -m "exiftool"  # Only tests requiring exiftool
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

```
oncutf/
├── core/                   # Core application components
│   ├── application_context.py  # Application-wide context
│   ├── backup_manager.py   # Database backup system
│   ├── metadata_manager.py # Metadata operations
│   └── ...
├── models/                 # Data models
├── modules/                # Rename logic modules
├── utils/                  # Utility functions
├── widgets/                # PyQt5 UI components
├── tests/                  # Test suite
├── docs/                   # Documentation
└── resources/              # Application resources
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
- **ExifTool tests** (`@pytest.mark.exiftool`) - Tests requiring ExifTool

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

The application uses structured logging. Set log level in `config.py`:

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
# In config.py
DEBUG_RESET_DATABASE = True  # Reset database on startup
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run quality checks: `make lint && make format && make type-check`
5. Run tests: `make test`
6. Commit with a descriptive message
7. Push and create a pull request

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

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

**ExifTool not found:**
```bash
# Install ExifTool
# Ubuntu/Debian
sudo apt-get install exiftool

# macOS
brew install exiftool

# Windows: Download from https://exiftool.org/
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
