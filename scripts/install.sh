#!/usr/bin/env bash
set -euo pipefail

# Claude Code Lark Bridge — One-Line Install
# Usage: curl -fsSL https://raw.githubusercontent.com/xujie8867/claude-code-lark-bridge/master/scripts/install.sh | bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔗 Claude Code Lark Bridge Installer${NC}"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is required but not installed.${NC}"
    echo "   Install from: https://nodejs.org (v18+)"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}❌ Node.js v18+ required. Current: $(node -v)${NC}"
    exit 1
fi
echo -e "  ✓ Node.js $(node -v)"

# Install lark-cli
echo -e "${YELLOW}📦 Installing @larksuite/cli...${NC}"
npm install -g @larksuite/cli

# Clone or download skills
CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
REPO_DIR="/tmp/claude-code-lark-bridge"

if [ -d "$REPO_DIR" ]; then
    rm -rf "$REPO_DIR"
fi

echo -e "${YELLOW}📥 Downloading skills...${NC}"
git clone --depth 1 https://github.com/xujie8867/claude-code-lark-bridge.git "$REPO_DIR" 2>/dev/null || {
    echo -e "${YELLOW}⚠ git clone failed, trying download...${NC}"
    curl -fsSL https://github.com/xujie8867/claude-code-lark-bridge/archive/refs/heads/master.tar.gz | tar xz -C /tmp/
    mv /tmp/claude-code-lark-bridge-master "$REPO_DIR"
}

mkdir -p "$SKILLS_DIR"
cp -r "$REPO_DIR/skills/"* "$SKILLS_DIR/"
rm -rf "$REPO_DIR"

echo -e "${GREEN}✅ Skills installed to ${SKILLS_DIR}${NC}"

# Init config
echo -e "${YELLOW}🔧 Initializing lark-cli config...${NC}"
lark-cli config init --new 2>/dev/null || {
    echo -e "${YELLOW}⚠ Config may already exist. Run 'lark-cli config init --new' manually if needed.${NC}"
}

echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"
echo ""
echo -e "  Verify:  ${YELLOW}lark-cli auth status${NC}"
echo -e "  Skills:  ${YELLOW}ls ~/.claude/skills/${NC}"
echo -e "  Docs:    ${YELLOW}https://github.com/xujie8867/claude-code-lark-bridge${NC}"
echo ""
