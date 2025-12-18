import solara

# 1. 建立一個「響應式」變數
name = solara.reactive("Guest")

@solara.component
def Page():
    
    # 標題區塊
    with solara.Column(align="center"):
        solara.Markdown("""
        ## 澎湖珊瑚礁與相關生態網站
        """)

    # 簡介區塊
    solara.Markdown("## 簡介")
    solara.Markdown("澎湖島在台灣本專案運用 Google Earth Engine 的開放資料，分類與分析 2015 年至 2025 年間的衛星影像，試圖從數據中拼湊出珊瑚礁棲地的消長。是一份關於時間、海洋與變化的故事，希望能透過視覺化的數據，讓我們看見海洋的呼吸，並共同思考永續共存的未來。")
