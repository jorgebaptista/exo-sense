@echo off
REM 🚀 ExoSense Pre-Commit Quality Checks (Windows)
REM Runs all CI checks locally before pushing to avoid CI failures

echo 🎯 Starting ExoSense Pre-Commit Quality Checks...
echo ==============================================

REM Get the project root (assuming script is in scripts/ folder)
set PROJECT_ROOT=%~dp0..
cd /d "%PROJECT_ROOT%"

echo Project root: %PROJECT_ROOT%

REM Track overall status
set OVERALL_STATUS=0

echo.
echo === 🎨 FRONTEND CHECKS ===
cd /d "%PROJECT_ROOT%\frontend"
echo 🔍 Frontend TypeScript Check...
call npm run type-check
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 Frontend ESLint...
call npm run lint  
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 Frontend Tests...
call npm test -- --passWithNoTests
if errorlevel 1 set OVERALL_STATUS=1

echo.
echo === 🐍 BACKEND API CHECKS ===
cd /d "%PROJECT_ROOT%\api"
echo 🔍 API MyPy Type Check...
call mypy .
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 API Ruff Lint...
call ruff check .
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 API Ruff Format Check...
call ruff format --check .
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 API Tests...
call pytest tests/ -v
if errorlevel 1 set OVERALL_STATUS=1

echo.
echo === 🤖 ML PACKAGE CHECKS ===
cd /d "%PROJECT_ROOT%\ml"
echo 🔍 ML MyPy Type Check...
call mypy . --explicit-package-bases
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 ML Ruff Lint...
call ruff check .
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 ML Ruff Format Check...
call ruff format --check .
if errorlevel 1 set OVERALL_STATUS=1

echo 🔍 ML Tests...
call pytest tests/ -v
if errorlevel 1 set OVERALL_STATUS=1

echo.
echo ==============================================
echo 🎯 PRE-COMMIT CHECKS SUMMARY
echo ==============================================

if %OVERALL_STATUS%==0 (
    echo 🎉 ALL CHECKS PASSED! ✅
    echo    Ready to commit and push! 🚀
) else (
    echo 🚨 SOME CHECKS FAILED! ❌
    echo    Please fix the issues above before committing.
    echo.
    echo Quick fixes:
    echo   • Formatting: Run 'cd api && ruff format .' or 'cd ml && ruff format .'
    echo   • Linting: Check the specific error messages above
    echo   • Types: Review MyPy errors and add proper type annotations
    echo   • Tests: Make sure all tests pass locally
)

cd /d "%PROJECT_ROOT%"
pause
exit /b %OVERALL_STATUS%