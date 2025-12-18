import solara
import leafmap

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
    # 建立一個容器來放地圖，設定高度為 500px，確保地圖能顯示出來
    with solara.Column(style={"height": "500px", "width": "100%"}):
        
        # 1. 建立地圖，使用混合衛星圖 (Hybrid) 以便觀察珊瑚礁與海岸線
        m = leafmap.Map(google_map="HYBRID")

        # 2. 設定研究區域座標 (澎湖範圍)
        # 格式: [min_lon, min_lat, max_lon, max_lat]
        bounds = [119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108]

        # 3. 畫出紅色框框標示範圍
        # fill=False 表示不填滿顏色，只留紅框，才不會擋住地圖
        m.add_bbox(bounds, color="red", weight=3, opacity=0.8, fill=False)

        # 4. 讓鏡頭自動飛到這個範圍
        m.zoom_to_bounds(bounds)

        # 5. 顯示地圖元件
        m.element()
