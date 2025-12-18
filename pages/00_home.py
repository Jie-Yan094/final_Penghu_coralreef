import solara
import leafmap.leafmap as leafmap

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

    solara.Markdown("## 研究區域")

    with solara.Column(style={"height": "500px", "width": "100%"}):
        
        # ✅ 強制設定法：直接指定 center (中心點) 和 zoom (縮放層級)
        # center = [緯度 Lat, 經度 Lon] -> 我算好澎湖中心大概在 [23.52, 119.54]
        # zoom = 11 -> 這個大小剛好可以看到整個群島
        m = leafmap.Map(
            center=[23.52, 119.54], 
            zoom=11, 
            google_map="HYBRID"
        )

        # 這裡依然畫上紅框框，讓讀者知道確切範圍
        bounds = [119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108]
        m.add_bbox(bounds, color="red", weight=3, opacity=0.8, fill=False)

        # 這一行 m.zoom_to_bounds(bounds) 可以刪掉了，因為我們上面已經強制設定好位置了
        
        m.element()
