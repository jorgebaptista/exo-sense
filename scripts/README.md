# 🚀 ExoSense Development Scripts

This directory contains helpful scripts to streamline your development workflow and avoid CI failures.

## 📋 Available Scripts

### 🎯 `pre-commit-checks.sh` / `pre-commit-checks.bat`
**Purpose**: Run all CI checks locally before pushing to avoid CI failures

**Usage**:
```bash
# Linux/macOS/Git Bash
./scripts/pre-commit-checks.sh

# Windows Command Prompt
scripts\pre-commit-checks.bat
```

**What it checks**:
- ✅ Frontend TypeScript compilation
- ✅ Frontend ESLint linting  
- ✅ Frontend Jest tests
- ✅ Backend MyPy type checking
- ✅ Backend Ruff linting
- ✅ Backend Ruff formatting
- ✅ Backend Pytest tests
- ✅ ML MyPy type checking
- ✅ ML Ruff linting
- ✅ ML Ruff formatting
- ✅ ML Pytest tests
- 🐳 Docker build (optional)

### 🛠️ `fix-all.sh`
**Purpose**: Automatically fix common formatting and linting issues

**Usage**:
```bash
./scripts/fix-all.sh
```

**What it fixes**:
- 🔧 Code formatting (Ruff format)
- 🔧 Auto-fixable linting issues (Ruff --fix)

## 🔄 Recommended Workflow

1. **Before starting work**:
   ```bash
   git pull origin main
   ./scripts/pre-commit-checks.sh  # Ensure clean baseline
   ```

2. **During development**:
   ```bash
   # Make your changes...
   ./scripts/fix-all.sh             # Auto-fix formatting
   ./scripts/pre-commit-checks.sh   # Verify everything passes
   ```

3. **Before committing**:
   ```bash
   ./scripts/pre-commit-checks.sh   # Final check
   git add .
   git commit -m "Your commit message"
   git push
   ```

## 📊 Output Examples

### ✅ All Checks Pass:
```
🎉 ALL CHECKS PASSED! ✅
   Ready to commit and push! 🚀
```

### ❌ Some Checks Fail:
```
🚨 SOME CHECKS FAILED! ❌
   Please fix the issues above before committing.

Quick fixes:
  • Formatting: Run 'cd api && ruff format .' or 'cd ml && ruff format .'
  • Linting: Check the specific error messages above  
  • Types: Review MyPy errors and add proper type annotations
  • Tests: Make sure all tests pass locally
```

## 🎯 Benefits

- ⚡ **Faster feedback** - catch issues locally instead of waiting for CI
- 🛡️ **Avoid CI failures** - run the same checks CI runs
- 🔧 **Auto-fix** - automatically fix formatting issues
- 📊 **Clear reporting** - see exactly what passed/failed
- 🎨 **Colorized output** - easy to scan results

## 🔧 Troubleshooting

### Docker Issues
If Docker checks fail:
- Make sure Docker Desktop is running
- Docker checks are optional for local development
- CI will still test Docker builds

### Permission Issues
If scripts won't run:
```bash
chmod +x scripts/*.sh
```

### Path Issues
Run scripts from the project root:
```bash
cd /path/to/exo-sense
./scripts/pre-commit-checks.sh
```