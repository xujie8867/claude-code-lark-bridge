# Claude Code Lark Bridge

一键接入飞书（Lark/Feishu）到 Claude Code，让 AI Agent 获得 26 种飞书操作能力。

## 功能

| 模块 | 能力 |
|------|------|
| lark-im | 即时通讯（收发消息、群聊管理） |
| lark-base | 多维表格（数据库、字段、记录） |
| lark-doc | 云文档 / Wiki |
| lark-sheets | 电子表格 |
| lark-calendar | 日历、日程、会议室 |
| lark-drive | 云空间、文件管理 |
| lark-mail | 邮箱 |
| lark-contact | 通讯录 |
| lark-task | 任务管理 |
| lark-approval | 审批 |
| lark-okr | OKR |
| lark-wiki | 知识库 |
| lark-vc | 视频会议 |
| lark-vc-agent | 会议纪要 Agent |
| lark-minutes | 妙记（语音转文字） |
| lark-slides | 幻灯片 |
| lark-markdown | Markdown 文件管理 |
| lark-apps | 妙搭（Miaoda）部署 |
| lark-attendance | 考勤 |
| lark-event | 事件订阅 |
| lark-openapi-explorer | API 浏览器 |
| lark-skill-maker | 自定义 Skill 创建 |
| lark-whiteboard | 白板 |
| lark-workflow-meeting-summary | 会议总结 |
| lark-workflow-standup-report | 站会报告 |

## 快速开始

### 1. 安装 lark-cli

```bash
npm install -g @larksuite/cli
```

### 2. 部署 Skills

```bash
# 克隆本仓库
git clone https://github.com/xujie8867/claude-code-lark-bridge.git

# 复制 Skills 到 Claude Code 目录
cp -r claude-code-lark-bridge/skills/* ~/.claude/skills/
```

### 3. 初始化配置

```bash
lark-cli config init --new
```

扫码完成飞书应用授权。

### 4. 验证

```bash
lark-cli auth status
# 应显示 Bot identity: ready
```

## 两种身份模式

| 模式 | 身份 | 使用 |
|------|------|------|
| Bot | `--as bot` | 应用级操作，配置后即可使用 |
| User | `--as user` | 需 `lark-cli auth login` 授权 |

## 使用示例

```
用户: "帮我查最近的聊天记录"
用户: "创建一个项目跟踪多维表格"
用户: "把这个 HTML 部署到飞书妙搭"
```

AI 自动识别飞书相关请求并加载对应 Skill。

## Windows

```powershell
npm install -g @larksuite/cli
git clone https://github.com/xujie8867/claude-code-lark-bridge.git
xcopy claude-code-lark-bridge\skills\* %USERPROFILE%\.claude\skills\ /E /I
lark-cli config init --new
```
