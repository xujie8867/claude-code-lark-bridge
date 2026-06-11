#!/usr/bin/env bash
set -euo pipefail

# Validate all skills in the repository
# Usage: ./scripts/validate-skills.sh

SKILLS_DIR="$(cd "$(dirname "$0")/../skills" && pwd)"
ERRORS=0
WARNINGS=0

echo "🔍 Validating skills in $SKILLS_DIR"
echo ""

for skill_dir in "$SKILLS_DIR"/*/; do
    skill=$(basename "$skill_dir")
    
    # Check SKILL.md exists
    if [ ! -f "${skill_dir}SKILL.md" ]; then
        echo "  ❌ $skill: Missing SKILL.md"
        ERRORS=$((ERRORS + 1))
        continue
    fi
    
    # Check SKILL.md is not empty
    if [ ! -s "${skill_dir}SKILL.md" ]; then
        echo "  ❌ $skill: SKILL.md is empty"
        ERRORS=$((ERRORS + 1))
        continue
    fi
    
    # Check for required metadata
    if ! grep -q "^name:" "${skill_dir}SKILL.md"; then
        echo "  ⚠ $skill: Missing 'name' in frontmatter"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    if ! grep -q "^description:" "${skill_dir}SKILL.md"; then
        echo "  ⚠ $skill: Missing 'description' in frontmatter"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Count references
    REF_COUNT=$(find "$skill_dir" -name "*.md" -not -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    
    # Count assets
    ASSET_COUNT=$(find "$skill_dir/assets" -type f 2>/dev/null | wc -l | tr -d ' ')
    
    echo "  ✓ $skill (${REF_COUNT} refs, ${ASSET_COUNT} assets)"
done

echo ""
SKILL_COUNT=$(ls -d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l | tr -d ' ')
echo "Total: $SKILL_COUNT skills | $ERRORS errors | $WARNINGS warnings"

if [ $ERRORS -gt 0 ]; then
    exit 1
fi
