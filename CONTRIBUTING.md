# Contributing to f3-nation-data

Welcome to the f3-nation-data project! We're excited to have you contribute.
This guide will help you set up your development environment and get started.

## 🛠️ Development Environment Setup

This project uses [mise](https://mise.jdx.dev/) for managing development tools
and [Starship](https://starship.rs/) for a consistent shell prompt experience.

> **📚 Need detailed setup instructions?** Check out our comprehensive
> development setup documentation in the
> [F3 NOHO development guide](https://github.com/f3noho) for platform-specific
> instructions including Windows.

### Prerequisites

- **Shell**: Any modern shell (bash, zsh, fish, etc.)
- **Terminal**: A terminal that supports
  [Nerd Fonts](https://www.nerdfonts.com/) (recommended for optimal Starship
  experience)

### Quick Setup

1. **Install mise** following the
   [installation guide](https://mise.jdx.dev/getting-started.html)
2. **Configure your shell** to activate mise (see examples below)
3. **Navigate to project** and run `mise install`
4. **Install dependencies** with `uv sync`

### Shell Configuration Examples

Add mise activation to your shell configuration:

**Bash** (`~/.bashrc`):

```bash
eval "$(~/.local/bin/mise activate bash)"

# Optional: Enable starship prompt when available
if command -v starship &> /dev/null; then
    eval "$(starship init bash)"
fi
```

**Zsh** (`~/.zshrc`):

```bash
eval "$(mise activate zsh)"

# Optional: Enable starship prompt when available
if command -v starship &> /dev/null; then
    eval "$(starship init zsh)"
fi
```

## 🐍 Python Development

This project uses `uv` for Python package management and `tbelt` for task
automation. Thanks to mise's automatic virtual environment activation, you don't
need to manually manage virtual environments!

### Install Dependencies

```bash
# Install all dependencies (mise auto-activates the virtual environment)
uv sync
```

### Running Tasks

```bash
# Run all CI checks (Python, types, complexity, coverage, prettier)
poe ci-checks

# Run individual checks
poe check-python    # Code formatting and linting
poe check-types     # Type checking with basedpyright
poe check-complexity # Code complexity analysis
poe check-coverage  # Test coverage analysis
poe check-prettier  # Code formatting for JS/TS/JSON/MD files
```

### Auto-Fix Formatting Issues

Most formatting issues can be automatically fixed using `tb format` commands:

```bash
# Fix Python formatting issues
tb format python

# Fix JS/TS/JSON/Markdown formatting issues
tb format prettier
```

> **💡 Tip:** Run the format commands before running checks to automatically
> resolve most formatting issues!

## 🔧 Development Tasks

```bash
# Sync all dependencies
poe uv-sync

# Install new Python dependency
uv add package-name

# Install development dependency
uv add --dev package-name

# Update all tools
mise upgrade

# Check mise status
mise doctor
```

### Optional: Enable Poe Task Autocompletion

For enhanced developer experience, you can enable shell autocompletion for poe
tasks. This provides tab completion for all available tasks.

See the
[official poe shell completion guide](https://poethepoet.natn.io/installation.html#shell-completion)
for detailed instructions covering bash, zsh, fish, and other shells.

**Quick example for bash:**

```bash
# System-wide installation
poe _bash_completion | sudo tee /etc/bash_completion.d/poe.bash-completion > /dev/null

# Then restart your shell or run:
source ~/.bashrc
```

After setup, you can use tab completion: `poe c[tab]` → `poe ci-checks`

## 💡 What You Get

- ✅ **Automatic tool activation** when you enter the project
- ✅ **Virtual environment auto-management** via mise + uv
- ✅ **Consistent development environment** across all contributors
- ✅ **Beautiful shell prompt** with git/Python info (optional starship)
- ✅ **No global tool conflicts** - everything is project-scoped

## 🤝 Contributing Guidelines

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run code quality checks
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📞 Getting Help

- **F3 NOHO Development Guide** - Comprehensive setup documentation (coming
  soon)
- [mise documentation](https://mise.jdx.dev/) - Tool management
- [Starship documentation](https://starship.rs/) - Shell prompt customization
- **Issues** - Open an issue for project-specific problems

Happy coding! 🎉
