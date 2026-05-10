@echo off
setlocal

echo === Gamma4 GitHub Sync ===
git status --short

echo.
echo Adding changes...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add failed. Push aborted.
    goto end
)

echo.
echo Checking for changes...
git diff --cached --quiet
if %errorlevel%==0 (
    echo No changes to commit.
    goto end
)

echo.
set /p commit_msg="Enter commit message (press Enter for default 'update'): "
if "%commit_msg%"=="" set commit_msg=update

echo.
echo Committing changes...
git commit -m "%commit_msg%"
if %errorlevel% neq 0 (
    echo [ERROR] git commit failed. Push aborted.
    goto end
)

echo.
echo Pushing to GitHub...
git push
if %errorlevel% neq 0 (
    echo [ERROR] git push failed.
    goto end
)

:end
echo.
echo Sync completed.
pause
