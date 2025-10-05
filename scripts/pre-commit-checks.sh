#!/bin/bash

# 🚀 ExoSense Pre-Commit Quality Checks
# Runs all CI checks locally before pushing to avoid CI failures

set -e  # Exit on any error

echo "🎯 Starting ExoSense Pre-Commit Quality Checks..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

# Function to run a check and track status
run_check() {
    local check_name="$1"
    local check_command="$2"
    local working_dir="$3"
    
    echo -e "\n${BLUE}🔍 Running: $check_name${NC}"
    echo "   Directory: $working_dir"
    echo "   Command: $check_command"
    
    if cd "$working_dir" && eval "$check_command"; then
        echo -e "${GREEN}✅ PASSED: $check_name${NC}"
    else
        echo -e "${RED}❌ FAILED: $check_name${NC}"
        OVERALL_STATUS=1
    fi
}

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Project root: $PROJECT_ROOT"

# 🎨 Frontend Checks
echo -e "\n${YELLOW}=== 🎨 FRONTEND CHECKS ===${NC}"
run_check "Frontend TypeScript Check" "npm run type-check" "$PROJECT_ROOT/frontend"
run_check "Frontend ESLint" "npm run lint" "$PROJECT_ROOT/frontend" 
run_check "Frontend Tests" "npm test -- --passWithNoTests" "$PROJECT_ROOT/frontend"

# 🐍 Backend API Checks  
echo -e "\n${YELLOW}=== 🐍 BACKEND API CHECKS ===${NC}"
run_check "API MyPy Type Check" "mypy ." "$PROJECT_ROOT/api"
run_check "API Ruff Lint" "ruff check ." "$PROJECT_ROOT/api"
run_check "API Ruff Format Check" "ruff format --check ." "$PROJECT_ROOT/api"
run_check "API Tests" "pytest tests/ -v" "$PROJECT_ROOT/api"

# 🤖 ML Package Checks
echo -e "\n${YELLOW}=== 🤖 ML PACKAGE CHECKS ===${NC}"
run_check "ML MyPy Type Check" "PYTHONPATH=src mypy . --explicit-package-bases" "$PROJECT_ROOT/ml"
run_check "ML Ruff Lint" "ruff check ." "$PROJECT_ROOT/ml"
run_check "ML Ruff Format Check" "ruff format --check ." "$PROJECT_ROOT/ml"
run_check "ML Tests" "PYTHONPATH=src pytest tests/ -v" "$PROJECT_ROOT/ml"

# 🐳 Docker Build Test (Optional - only if Docker is available)
echo -e "\n${YELLOW}=== 🐳 DOCKER BUILD TEST ===${NC}"
if command -v docker &> /dev/null && docker info &>/dev/null; then
    echo -e "${BLUE}🐳 Docker found and running - running build test${NC}"
    run_check "Docker Build" "docker build -t exosense-api-test ." "$PROJECT_ROOT/api"
    
    # Clean up test image
    docker rmi exosense-api-test &>/dev/null || true
else
    echo -e "${YELLOW}⚠️  Docker not available or not running - skipping Docker build test${NC}"
    echo -e "${YELLOW}   (This is optional for local development)${NC}"
fi

# 📊 Final Results
echo -e "\n${YELLOW}=============================================="
echo "🎯 PRE-COMMIT CHECKS SUMMARY"
echo "=============================================="

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED! ✅${NC}"
    echo -e "${GREEN}   Ready to commit and push! 🚀${NC}"
    exit 0
else
    echo -e "${RED}🚨 SOME CHECKS FAILED! ❌${NC}"
    echo -e "${RED}   Please fix the issues above before committing.${NC}"
    echo ""
    echo "Quick fixes:"
    echo "  • Formatting: Run 'cd api && ruff format .' or 'cd ml && ruff format .'"
    echo "  • Linting: Check the specific error messages above"
    echo "  • Types: Review MyPy errors and add proper type annotations"
    echo "  • Tests: Make sure all tests pass locally"
    exit 1
fi