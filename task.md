# 開發任務進度表 (Task List)

## 核心基礎建設
- [x] 建立基礎數據抓取模組 (`fetch_yf.py`)
- [x] 實作技術指標運算庫 (`indicators.py`)
- [x] 完成向量化回測引擎核心 (`backtest.py`)
- [x] 修正 Import Path 引用錯誤 (Streamlit 相容性)

## UI 視覺化與交互
- [x] 開發 Streamlit 儀表板 (`app.py`)
- [x] 實作 K 線圖與買賣點標記圖表 (`charting.py`)
- [x] 建立資產淨值曲線圖
- [x] 介面與輸出內容全面繁體中文化

## 智慧化與預測功能 [NEW]
- [x] 實作 AI 預測模組 (`predictor.py`) - 基於線性回歸
- [x] 實作綜合投資評估系統 (給予建議與評分)
- [x] 整合預測趨勢圖至儀表板
- [x] 新增信心區間 (Confidence Interval) 視覺化

## 用戶體驗優化
- [x] 建立 Windows 一鍵啟動腳本 (`Run_Dashboard.bat`)
- [x] 建立資料更新捷徑 (`Update_Data.bat`)
- [x] 修正 yfinance 身份識別警告 (加入 User-Agent)
- [x] 更新完整文件 (README, Walkthrough)

## 待辦事項 (Future Backlog)
- [ ] 增加多標的市場掃描器 (Scanner)
- [ ] 支援 Telegram 機器人通知
- [ ] 引入更多複雜模型 (如 LSTM, Random Forest)
