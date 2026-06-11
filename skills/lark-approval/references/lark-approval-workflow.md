# Lark Approval — Common Workflows

## Check Pending Approvals
```bash
lark-cli approval +get-pending --as user
```

## Approve/Reject an Instance
```bash
lark-cli approval +approve --instance <instance_id> --comment "Approved"
lark-cli approval +reject --instance <instance_id> --comment "Needs revision"
```

## View My Submitted Approvals
```bash
lark-cli approval +get-my-requests --as user
```

## Tips
- Approval instances are identified by `instance_id`
- Comments are optional but recommended for rejections
- Use `--as user` for personal approval actions
