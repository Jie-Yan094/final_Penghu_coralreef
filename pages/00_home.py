import solara
import leafmap.leafmap as leafmap

# 1. 建立一個「響應式」變數
name = solara.reactive("Guest")

@solara.component
def Page():
    
    # ✅ 修改 1：建立一個「最外層」容器，設定 align="center"
    # style={"text-align": "center"} 確保 Markdown 文字內容也置中
    with solara.Column(align="center", style={"text-align": "center", "width": "100%"}):
        
        # --- 標題區塊 ---
        solara.Markdown("## 澎湖珊瑚礁與相關生態網站")

        # --- 簡介區塊 ---
        solara.Markdown("### 簡介") # 改用 ### 看起來層級比較對
        
        # 為了讓閱讀舒適，這裡可以限制文字寬度，不然在大螢幕會太寬
        with solara.Column(style={"max-width": "800px"}):
            solara.Markdown(
                "澎湖島在台灣本專案運用 Google Earth Engine 的開放資料，"
                "分類與分析 2015 年至 2025 年間的衛星影像，試圖從數據中拼湊出珊瑚礁棲地的消長。"
                "是一份關於時間、海洋與變化的故事，希望能透過視覺化的數據，"
                "讓我們看見海洋的呼吸，並共同思考永續共存的未來。"
            )

        solara.Markdown("### 研究區域")

        # --- 地圖區塊 ---
        # ✅ 修改 2：地圖容器設定寬度 80%，因為外層有 align="center"，它會自動居中
        with solara.Column(style={"height": "600px", "width": "80%"}):
            
            # 初始化地圖
            m = leafmap.Map(
                center=[23.52, 119.54], 
                zoom=11, 
                google_map="HYBRID"
            )

            # 畫紅框
            bounds = [119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108]
            m.add_bbox(bounds, color="red", weight=3, opacity=0.8, fill=False)
            
            # ✅ 修改 3：移除了 return！
            # 直接使用 display，這樣地圖才會乖乖待在標題下方
            solara.display(m)
