@echo off
title Stock Data Updater
color 0a

echo ==========================================
echo       STOCK DATA UPDATER
echo ==========================================
echo.
set /p symbol="Enter Stock Symbol (e.g. 2330.TW or AAPL): "
set /p period="Enter Period (default 5y): "

if "%period%"=="" set period=5y

echo.
echo Fetching data for %symbol%...
py src/fetch_yf.py --symbol %symbol% --period %period%

echo.
echo Done! Data saved in data/ folder.
echo.
pause
