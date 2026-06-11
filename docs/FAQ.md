# Frequently Asked Questions

## General

### What is Claude Code Lark Bridge?
A collection of 26 skills that gives Claude Code the ability to interact with Lark/Feishu — the enterprise collaboration platform.

### Do I need programming skills to use this?
No. Once installed, you interact with Lark through natural language in Claude Code. Just ask for what you need.

### Is this official?
No. This is an independent open-source project, not affiliated with Anthropic or Lark/Feishu.

## Installation

### Why do I need lark-cli?
`lark-cli` is the command-line tool that handles authentication and API communication with Lark/Feishu. The skills wrap `lark-cli` commands for AI agent use.

### Can I use this without a Lark/Feishu account?
No. You need a Lark/Feishu account to use the skills. The free tier works for most use cases.

### Does this work on Windows?
Yes. The skills are platform-independent. See the Windows setup section in README.

## Usage

### What identity mode should I use?
- `--as bot`: For app-level operations (recommended for automation)
- `--as user`: For personal account operations

### Can I create custom skills?
Yes! Use the `lark-skill-maker` skill to wrap new Lark API operations.

### How do I troubleshoot auth errors?
1. Run `lark-cli auth status`
2. If expired, run `lark-cli auth login`
3. Check the [troubleshooting guide](../skills/lark-shared/references/lark-shared-troubleshooting.md)

## Security

### Where are my credentials stored?
Credentials are managed by `lark-cli` and stored in `~/.lark-cli/`.

### Can I use this in production?
Yes, but review the security implications for your organization. The MIT license comes with no warranty.
