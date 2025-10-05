#!/bin/bash

# 🛠️ ExoSense Auto-Fix Script
# Automatically fixes common formatting and linting issues

set -e

echo "🛠️ ExoSense Auto-Fix Script"
echo "=========================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Project root: $PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\n${BLUE}🔧 Auto-fixing formatting issues...${NC}"

# Fix API formatting
echo "Fixing API formatting..."
cd "$PROJECT_ROOT/api"
ruff format .
echo -e "${GREEN}✅ API formatting fixed${NC}"

# Fix ML formatting  
echo "Fixing ML formatting..."
cd "$PROJECT_ROOT/ml"
ruff format .
echo -e "${GREEN}✅ ML formatting fixed${NC}"

# Try to auto-fix some linting issues
echo -e "\n${BLUE}🔧 Auto-fixing linting issues...${NC}"

cd "$PROJECT_ROOT/api"
ruff check --fix . || echo "Some linting issues require manual attention"

cd "$PROJECT_ROOT/ml"  
ruff check --fix . || echo "Some linting issues require manual attention"

echo -e "\n${GREEN}🎉 Auto-fix complete!${NC}"
echo "Run the pre-commit checks to see remaining issues:"
echo "  ./scripts/pre-commit-checks.sh"