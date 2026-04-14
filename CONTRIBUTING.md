# Contributing to Snowflake Cortex Agents SDK

Thank you for considering contributing to the Snowflake Cortex Agents SDK! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- Your environment (Python version, OS, package version)
- Minimal code example demonstrating the issue

### Suggesting Features

Feature requests are welcome! Please:
- Check existing issues to avoid duplicates
- Clearly describe the feature and use case
- Explain why this feature would be useful to most users

### Pull Requests

#### Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
- **uv** (fast Python package manager): [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (using PowerShell)
  powershell -ExecutionPolicy BypassUser -c "irm https://astral.sh/uv/install.ps1 | iex"

  # Or via pip
  pip install uv
  ```

#### Setup Steps

1. **Fork the repository** and create your branch from `main`

2. **Clone and set up development environment**:
   ```bash
   git clone https://github.com/ChuliangXiao/snowflake-cortex-agents.git
   cd snowflake-cortex-agents

   # Sync dependencies (installs all dev, test, and doc tools)
   make sync
   # Or manually: uv sync --all-extras
   ```

3. **Make your changes**:
   - Follow the existing code style (PEP 8)
   - Add type hints to all functions
   - Update docstrings for any changed functionality
   - Add tests for new features

4. **Run tests and checks**:

   Using **Makefile** (recommended):
   ```bash
   make format    # Format and fix code
   make lint      # Run linter
   make ty        # Type checking
   make tests     # Run tests (without coverage)
   make check     # Run all checks at once
   make coverage  # Run tests with coverage report
   ```

   Or directly with **uv**:
   ```bash
   uv run ruff format cortex_agents/ examples/ tests/
   uv run ruff check cortex_agents/ examples/ tests/
   uv run ty check cortex_agents/
   uv run pytest
   uv run coverage run -m pytest && uv run coverage report -m
   ```

5. **Update documentation**:
   - Update README.md if adding features
   - Add docstrings with examples
   - Update CHANGELOG.md under "Unreleased" section
   - Preview documentation locally:
     ```bash
     make serve-docs
     # Or: uv run mkdocs serve
     ```
     Then open http://localhost:8000 in your browser

6. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add support for XYZ"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `test:` for test additions/changes
   - `refactor:` for code refactoring
   - `chore:` for maintenance tasks

7. **Push and create a Pull Request**:
   ```bash
   git push origin your-branch-name
   ```

   Then open a PR on GitHub with:
   - Clear description of changes
   - Reference to any related issues
   - Screenshots/examples if applicable

## Code Style Guidelines

- **Follow PEP 8** for Python code style
- **Use type hints** for all function parameters and returns
- **Write docstrings** using Google style:
  ```python
  def my_function(param1: str, param2: int) -> bool:
      """Brief description of function.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Description of return value

      Raises:
          ValueError: When param1 is empty

      Examples:
          >>> my_function("test", 42)
          True
      """
  ```
- **Keep functions focused** - single responsibility principle
- **Prefer composition over inheritance**
- **Use meaningful variable names**

## Testing Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use pytest for testing
- Mock external API calls (don't hit real Snowflake APIs in tests)
- Test both success and error cases

## Development Setup

### Optional: Pre-commit Hooks

Install pre-commit hooks for automatic code formatting:

```bash
uv sync --extra dev
uv run pre-commit install
```

This will automatically run ruff, ty, and other configured checks before each commit.

### Running Examples

To test examples locally:

```bash
# Set up environment variables
export SNOWFLAKE_ACCOUNT_URL="your-account.snowflakecomputing.com"
export SNOWFLAKE_PAT="your-token"

# Or copy .env.example to .env and fill in your values

# Run an example
uv run python examples/example_agent.py
```

## Questions?

If you have questions about contributing, feel free to:
- Open a discussion on GitHub
- Ask in an issue
- Reach out to the maintainers

Thank you for helping make this project better! 🚀
