@echo off
echo Resetting Git author for the entire history...
git rebase --root --exec "git commit --amend --reset-author --no-edit"
echo.
echo Force pushing to GitHub...
git push origin main --force
echo.
echo Process finished.
pause
