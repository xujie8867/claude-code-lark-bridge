#!/usr/bin/env bash
set -euo pipefail

# Claude Code Lark Bridge — One-Line Install
# Usage: curl -fsSL https://raw.githubusercontent.com/xujie8867/claude-code-lark-bridge/master/scripts/install.sh | bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    if [ -d "${REPO_DIR:-}" ]; then
        rm -rf "$REPO_DIR"
    fi
}
trap cleanup EXIT

echo -e "${GREEN}🔗 Claude Code Lark Bridge Installer${NC}"
echo ""

# Detect OS
OS="unknown"
case "$(uname -s)" in
    Darwin*)  OS="macOS" ;;
    Linux*)   OS="Linux" ;;
    MINGW*|MSYS*|CYGWIN*) OS="Windows" ;;
esac
echo -e "  ${CYAN}OS:${NC} $OS"

# Check Git (preferred for clone)
GIT_AVAILABLE=false
if command -v git &> /dev/null; then
    GIT_AVAILABLE=true
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is required but not installed.${NC}"
    case "$OS" in
        macOS)   echo "   Install: brew install node" ;;
        Linux)   echo "   Install: curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs" ;;
        Windows) echo "   Install: https://nodejs.org (v18+)" ;;
    esac
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}❌ Node.js v18+ required. Current: $(node -v)${NC}"
    exit 1
fi
echo -e "  ✓ Node.js $(node -v)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is required but not installed.${NC}"
    exit 1
fi
echo -e "  ✓ npm $(npm -v)"

# Install lark-cli
echo -e "${YELLOW}📦 Installing @larksuite/cli...${NC}"
npm install -g @larksuite/cli 2>&1 | tail -1
echo -e "  ✓ lark-cli $(lark-cli --version 2>/dev/null || echo 'installed')"

# Setup directories
CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
REPO_DIR="/tmp/claude-code-lark-bridge-$$"

mkdir -p "$SKILLS_DIR"

# Download skills
echo -e "${YELLOW}📥 Downloading skills (26 modules)...${NC}"
if [ "$GIT_AVAILABLE" = true ]; then
    git clone --depth 1 --quiet https://github.com/xujie8867/claude-code-lark-bridge.git "$REPO_DIR" 2>/dev/null || {
        echo -e "${YELLOW}⚠ git clone failed, falling back to tarball...${NC}"
        curl -fsSL https://github.com/xujie8867/claude-code-lark-bridge/archive/refs/heads/master.tar.gz | tar xz -C /tmp/
        mv /tmp/claude-code-lark-bridge-master "$REPO_DIR"
    }
else
    echo -e "${YELLOW}  git not found, downloading tarball...${NC}"
    curl -fsSL https://github.com/xujie8867/claude-code-lark-bridge/archive/refs/heads/master.tar.gz | tar xz -C /tmp/
    mv /tmp/claude-code-lark-bridge-master "$REPO_DIR"
fi

SKILL_COUNT=$(ls "$REPO_DIR/skills/" | wc -l | tr -d ' ')
cp -r "$REPO_DIR/skills/"* "$SKILLS_DIR/"
echo -e "  ✓ $SKILL_COUNT skills installed to $SKILLS_DIR"

# Init lark-cli config
echo -e "${YELLOW}🔧 Initializing lark-cli...${NC}"
if lark-cli config init --new 2>/dev/null; then
    echo -e "  ✓ Config initialized. Scan the QR code to complete auth."
else
    echo -e "${YELLOW}  ⚠ Config may already exist. Run 'lark-cli config init --new' if needed.${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"
echo ""
echo -e "  Verify auth:  ${CYAN}lark-cli auth status${NC}"
echo -e "  List skills:  ${CYAN}ls ~/.claude/skills/${NC}"
echo -e "  Docs:         ${CYAN}https://github.com/xujie8867/claude-code-lark-bridge${NC}"
echo ""
