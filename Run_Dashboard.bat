@echo off
title Trading Analysis Pro - Launching...
color 0b

echo ==========================================
echo       TRADING ANALYSIS PRO SYSTEM
echo ==========================================
echo.
echo [1/2] Checking and updating AI components...
py -m pip install streamlit plotly pandas yfinance requests scikit-learn --quiet

echo [2/2] Starting Professional Dashboard...
echo.
echo Browser will open automatically.
echo If not, visit: http://localhost:8501
echo.
echo ------------------------------------------

py -m streamlit run app.py

pause
