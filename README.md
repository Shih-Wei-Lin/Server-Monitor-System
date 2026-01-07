# 目的
- 透過SSH 抓取所有server CPU、MEM、Disk C的使用資源\
- 將抓取到的資源儲存在Mysql的資料庫裏面
- 透過抓取Mysql資料庫的資料後使用streamlit 建構網站

# 瀏覽器相容性建議（如遇顯示問題）
若瀏覽器出現以下狀況：

相關版本發布 [v1.0.0](http://192.168.1.81:3000/Server_Monitor/Server_Monitor_system/releases/tag/v1.0.0) 及問題 http://192.168.1.81:3000/Server_Monitor/Server_Monitor_system/issues/4

- 網頁無法顯示圖表
- 按鈕失靈或佈局錯亂
- 頁面卡住或白屏
## 請先嘗試安裝或更新以下瀏覽器：

👉 [Google Chrome](http://192.168.1.81:3000/Server_Monitor/Server_Monitor_system/releases/download/v1.0.0/ChromeStandaloneSetup64.exe)

👉 [Microsoft Edge](http://192.168.1.81:3000/Server_Monitor/Server_Monitor_system/releases/download/v1.0.0/MicrosoftEdgeEnterpriseX64.msi)

🔔 建議使用最新版本的 Chrome 或 Edge，因為 Streamlit 前端元件（如 Plotly、Altair）對舊版瀏覽器支援不佳。 