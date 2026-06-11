# Lark Shared — Troubleshooting Guide

## Common Issues

### Auth Token Expired
```bash
lark-cli auth login
# Follow the browser-based OAuth flow
```

### Bot Permission Denied
1. Ensure the Lark app has the required scopes
2. Check: `lark-cli auth status --as bot`
3. If missing scopes, update app configuration in Lark Developer Console

### Rate Limiting
- Lark API enforces rate limits per app
- Use exponential backoff: wait 1s, 2s, 4s, 8s...
- For bulk operations, add `--delay 500` between calls

### Identity Selection
- `--as bot`: Application-level operations (default)
- `--as user`: Personal account operations (requires `lark-cli auth login`)
