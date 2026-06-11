# Lark OpenAPI Explorer — Usage Guide

## When to Use
Use this skill when:
- No existing `lark-cli` command covers the needed operation
- You need to call a raw Lark OpenAPI endpoint
- You're exploring available API capabilities

## How It Works
1. Search for the relevant API endpoint from Lark's OpenAPI documentation
2. Construct the HTTP request with proper authentication
3. Execute via `lark-cli` with appropriate parameters

## Common Patterns

### GET Request
```bash
lark-cli openapi get --path "/open-apis/example/v1/resource" --as bot
```

### POST Request
```bash
lark-cli openapi post --path "/open-apis/example/v1/resource" --body '{"key": "value"}'
```

### With Query Parameters
```bash
lark-cli openapi get --path "/open-apis/example/v1/resource?page_size=20"
```
