# Lark Skill Maker — Quick Guide

## What is a Skill?
A Skill wraps one or more `lark-cli` commands into a reusable AI agent capability. Each skill has a `SKILL.md` that tells the AI:
- What the skill does
- When to use it
- How to execute commands
- Common pitfalls and workarounds

## Creating a New Skill
1. Create `skills/lark-<name>/SKILL.md`
2. Define metadata (name, version, description)
3. Add CRITICAL rules for the AI
4. Document commands and parameters
5. Add reference docs in `references/`
6. Add templates/icons in `assets/`

## Skill Template
```markdown
---
name: lark-example
version: 1.0.0
description: "Brief description"
metadata:
  requires:
    bins: ["lark-cli"]
---

# example

**CRITICAL — Read lark-shared first**

## Commands
### +command-name
Description.
```bash
lark-cli example +command --param value
```
```
