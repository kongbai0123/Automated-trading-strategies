@echo off
echo WARNING: This will reset all git history and make you the sole contributor.
echo.
pause

:: Remove existing git history
rd /s /q .git

:: Re-initialize
git init
git config user.name "kongbai0123"
git config user.email "ss93057885@gmail.com"

:: Add remote and push
git remote add origin https://github.com/kongbai0123/Automated-trading-strategies
git add .
git commit -m "Initial professional trading system launch"
git push origin main --force

echo.
echo SUCCESS: You are now the sole owner of this repository history.
pause
