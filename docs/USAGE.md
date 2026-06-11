# Usage Examples

Real-world examples of using Claude Code Lark Bridge Skills.

## Messaging

```
User: "Send a message to the product team group saying the release is ready"
→ lark-im: Searches for "产品团队" group, sends message via lark-cli im send
```

```
User: "Check if anyone mentioned me in Lark today"
→ lark-im: Searches recent messages across groups for @mentions
```

## Document Management

```
User: "Create a weekly report spreadsheet with columns: task, owner, status, deadline"
→ lark-sheets: Creates new sheet, sets headers, formats as table
```

```
User: "Read the PRD document and summarize the key requirements"
→ lark-doc: Fetches document content, analyzes and summarizes
```

## Calendar & Meetings

```
User: "Schedule a 30-minute standup for tomorrow 10am with the engineering team"
→ lark-calendar: Checks availability, creates event, adds attendees
```

```
User: "What happened in yesterday's project review meeting?"
→ lark-vc: Searches meeting history, retrieves minutes/summary
```

## Task Management

```
User: "Create a task for @zhangsan to review the API design by Friday"
→ lark-task: Creates task with assignee and due date
```

```
User: "Show me all my overdue tasks"
→ lark-task: Queries tasks, filters by due date < today
```

## Data & Analytics

```
User: "Create a Base table tracking customer feedback with sentiment analysis"
→ lark-base: Creates table with fields, sets up views and dashboard
```

## Email

```
User: "Draft a newsletter to all contributors about the v2.0 roadmap"
→ lark-mail: Creates draft with template, populates from contributor list
```

## Automation Workflows

```
User: "Generate a weekly meeting summary report"
→ lark-workflow-meeting-summary: Scans past week meetings, aggregates summaries
```

```
User: "What's on my plate today?"
→ lark-workflow-standup-report: Combines calendar agenda + pending tasks
```

## Deployment

```
User: "Deploy this HTML dashboard to Miaoda"
→ lark-apps: Packages HTML, deploys to 飞书妙搭, returns public URL
```

---

More examples: [docs/FAQ.md](docs/FAQ.md) | [ROADMAP.md](ROADMAP.md)
