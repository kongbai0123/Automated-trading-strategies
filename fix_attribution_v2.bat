@echo off
setlocal
echo 🚀 正在準備修正作者身份...

:: 嘗試對最近 10 次提交進行重設作者
:: 如果提交總數不足 10 次，這個指令可能會失敗，我們加入防錯
git rebase HEAD~10 --exec "git commit --amend --reset-author --no-edit"

if %errorlevel% neq 0 (
    echo ⚠️ 嘗試 10 次失敗，可能提交數不足。嘗試對所有提交進行修正...
    git rebase --root --exec "git commit --amend --reset-author --no-edit"
)

echo.
echo 📤 正在強制推送到 GitHub...
git push origin main --force

echo.
if %errorlevel% neq 0 (
    echo ❌ 修正失敗，請檢查上方 Git 錯誤訊息。
) else (
    echo ✅ 修正成功！請重新整理 GitHub。
)
pause
