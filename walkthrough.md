# 系統運作流程詳解 (System Walkthrough) - 專業預測版

本文件旨在協助您理解系統如何從原始數據，演進到 AI 預測與最終投資建議的完整路徑。

## 1. 核心資料流 (Data Pipeline)
系統遵循以下嚴謹的單向資料流：
**原始報價 (OHLCV) → 技術指標 (Indicators) → 策略訊號 (Strategy) → AI 預測與建議 (Predictor) → 績效評估 (Report)**

## 2. 模組深度解析

### 2.1 預測層 (Predictor Layer) [NEW]
*   **預測模型**：採用線性回歸 (Linear Regression) 針對最近 60 天的價格走勢進行建模。
*   **信心區間**：利用收盤價的標準差計算出預測的上、下界，量化市場波動風險。
*   **未來推演**：推算未來 10 個交易日的收盤價走勢，幫助使用者判斷目前趨勢是否具備延續性。

### 2.2 智慧決策邏輯 (Decision Logic)
系統會自動執行「三維度」評估：
1.  **動能維度**：檢查 RSI 是否處於超賣 (反彈機會) 或超買 (回擋風險)。
2.  **趨勢維度**：觀察短期與長期均線 (SMA 20/50) 的排列狀態。
3.  **策略維度**：確認內建策略是否觸發進場或出場訊號。
*最後將以上權重加總，產出最終的文字建議與警示顏色。*

### 2.3 回測與績效層
*   **T vs T+1 執行**：嚴格遵守今日收盤產生訊號，明日開盤執行，避免「未來資料偏誤」。
*   **資產變化**：即時計算複利下的資產淨值曲線 (Equity Curve)。

## 3. UI 交互設計與商品化升級 (Trading Workspace)
本次升級將原本的分析工具，徹底重構為對標專業 Trading SaaS (如 TradingView / Bloomberg) 的工作台體驗。

### 3.1 資訊層級重構 (Layered Architecture)
我們嚴格定義了視覺焦點的三層級結構：
1. **Primary (主圖區)**：K線圖佔據全寬 (Full Width)，不再與其他卡片並排。將 Signal Pill 整合於 K 線圖旁，明確化焦點。
2. **Secondary (指標區)**：RSI 與 MACD 指標圖表以 50%/50% 並排在 K 線圖正下方，讓使用者第一眼就能確認動能與趨勢。
3. **Tertiary (進階工具區)**：以 Tab 切換 `[📈 回測] [🔍 Scanner] [🤖 AI Projection] [📦 匯出]`。原本會搶佔主畫面焦點的 AI Decision Notes 與 Risk Radar 卡片已被收納至專屬的 AI Tab 中。

### 3.2 專業交易面板 (Market Status & Watchlist)
*   **🌐 Market Status Bar**：位於畫面上方，每 5 分鐘快取更新一次。提供加權指數 (^TWII)、NASDAQ (^IXIC)、BTC-USD 以及 VIX 恐慌指數的即時漲跌狀態與台灣時間。
*   **⭐ Watchlist (左欄)**：支援 Collapse (可收起) 的側邊列表，建立「看盤 → 挑標的 → 切換分析」的順暢 Workflow。點擊代碼即可瞬間載入該股票資料，取代過去每次都需要手動輸入的麻煩。

### 3.3 交易化 KPI 與回測基準
*   **8 欄專業 KPI**：將原本的基礎三指標擴充。新增「Win Rate (勝率)」、「Profit Factor (盈虧比)」、「Trades (交易次數)」、「Exposure (持倉比例)」以及「Calmar Ratio」，並加上對應的紅綠色視覺警示。
*   **Buy & Hold 基準線**：於「策略回測」區塊的資產淨值曲線 (Equity Curve) 中，疊加上一條灰色的 Buy & Hold 虛線。讓使用者能一目了然該策略是否跑贏單純的被動持有。

## 4. 未來擴充方向
*   **模型升級**：未來可引入 LSTM 或 Random Forest 進行非線性預測。
*   **多標的掃描**：一鍵掃描全市場符合「強力買入」評等的股票。
*   **圖表畫線工具**：未來考慮升級 Plotly 至 TradingView 輕量版套件，以支援使用者手動繪製趨勢線與費波那契回撤。

## 5. AI唯讀區
** 此為提供AI最佳化方向 ** 
1.  optimization/

