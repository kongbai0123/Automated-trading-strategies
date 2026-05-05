@echo off
echo 🚀 正在重寫 Git 歷史紀錄以修正作者身份...
git filter-branch -f --env-filter "GIT_AUTHOR_NAME='kongbai0123'; GIT_AUTHOR_EMAIL='ss93057885@gmail.com'; GIT_COMMITTER_NAME='kongbai0123'; GIT_COMMITTER_EMAIL='ss93057885@gmail.com';" --tag-name-filter cat -- --branches --tags
echo.
echo 📤 正在強制推送到 GitHub...
git push origin main --force
echo.
echo ✅ 修正完成！請前往 GitHub 查看貢獻者狀態。
pause
