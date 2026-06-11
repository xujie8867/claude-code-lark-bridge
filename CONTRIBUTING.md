# Contributing to Claude Code Lark Bridge

Thanks for your interest in contributing! This project bridges Claude Code with Lark/Feishu, and contributions of all kinds are welcome.

## Ways to Contribute

- **New Skills**: Add support for Lark APIs not yet covered
- **Bug fixes**: Improve existing skill implementations
- **Documentation**: Improve README, SKILL.md files, or translations
- **Testing**: Report bugs or help verify fixes
- **Ideas**: Suggest new features or improvements

## Development Workflow

### Prerequisites

- Node.js ≥ 18
- `@larksuite/cli` installed globally
- A Lark/Feishu account for testing

### Setting Up

```bash
git clone https://github.com/xujie8867/claude-code-lark-bridge.git
cd claude-code-lark-bridge
npm install -g @larksuite/cli
```

### Adding a New Skill

1. Create a directory under `skills/` with the skill name (e.g., `lark-my-skill/`)
2. Add a `SKILL.md` file following the [skill definition format](#skill-definition-format)
3. Optionally add `references/` for detailed operation guides
4. Optionally add `assets/` for templates, icons, etc.

### Skill Definition Format

Each `SKILL.md` should include:
- Skill name and description
- Supported commands/operations
- Required parameters
- Examples
- Error handling notes

### Commit Conventions

- `feat:` — New skill or feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `chore:` — Maintenance tasks
- `ci:` — CI/CD changes

### Pull Request Process

1. Fork the repo and create a branch
2. Make your changes
3. Test with `lark-cli` if applicable
4. Submit a PR with a clear description
5. Ensure CI checks pass

## Getting Help

- Open an [Issue](https://github.com/xujie8867/claude-code-lark-bridge/issues)
- Check existing [documentation](https://github.com/xujie8867/claude-code-lark-bridge#readme)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
