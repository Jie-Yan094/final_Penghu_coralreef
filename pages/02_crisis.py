import solara
import ipyleaflet  # 改用原生的 ipyleaflet
import geemap      # 僅用於 GEE 計算輔助
import ee
import os
import json
from google.oauth2.service_account import Credentials

# ==========================================
# 0. GEE 驗證與初始化
# ==========================================
try:
    key_content = os.environ.get('EARTHENGINE_TOKEN')
    if key_content:
        service_account_info = json.loads(key_content)
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/earthengine']
        )
        ee.Initialize(credentials=creds, project='ee-s1243037-0')
        print("✅ 雲端環境：GEE 驗證成功！")
    else:
        ee.Initialize(project='ee-s1243037-0')
        print("⚠️ 本機環境：使用預設驗證")
except Exception as e:
    print(f"❌ GEE 初始化失敗: {e}")

# ==========================================
# 1. 變數定義
# ==========================================
selected_year = solara.reactive(2024)

# ==========================================
# 2. 地圖組件 (純淨穩定版)
# ==========================================
@solara.component
def MapComponent(year):
    # A. 初始化地圖 (使用 ipyleaflet，完全無工具列負擔)
    # --------------------------------------------------
    def init_map():
        m = ipyleaflet.Map(
            center=[23.5, 119.5],
            zoom=11,
            scroll_wheel_zoom=True,
            layout={'height': '700px'}
        )
        # 加入混合底圖 (Hybrid)
        m.add_layer(ipyleaflet.Basemap.to_layer(ipyleaflet.basemaps.Esri.WorldImagery))
        # 疊加一點地名標籤 (Reference)
        m.add_layer(ipyleaflet.Basemap.to_layer(ipyleaflet.basemaps.CartoDB.PositronOnlyLabels))
        return m

    # 使用 use_memo 確保地圖只建立一次
    m = solara.use_memo(init_map, dependencies=[])

    # B. 更新圖層邏輯
    # --------------------------------------------------
    def update_layers():
        # 1. 移除舊的 GEE 圖層 (保留底圖)
        # ipyleaflet 的 layers 是一個 tuple，我們保留前兩層(底圖+標籤)
        if len(m.layers) > 2:
            m.layers = m.layers[:2]

        # 2. 定義 ROI 與 時間
        roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'

        # 3. GEE 運算
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                      .median()
                      .clip(roi))

        # 計算 NDCI
        ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')
        
        # 水體遮罩
        ndwi = collection.normalizedDifference(['B3', 'B8'])
        water_mask = ndwi.gt(0)
        ndci_masked = ndci.updateMask(water_mask)

        # 視覺參數
        palette = ['#0000ff', '#ffffff', '#00ff00', '#ffff00', '#ff0000']
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
        
        # 4. 轉換並加入圖層 (關鍵步驟)
        # 使用 geemap.ee_tile_layer 將 GEE 物件轉為 ipyleaflet 圖層
        try:
            layer = geemap.ee_tile_layer(ndci_masked, ndci_vis, name=f"{year} NDCI")
            m.add_layer(layer)
        except Exception as e:
            print(f"圖層載入失敗: {e}")

    # 監聽年份變化
    solara.use_effect(update_layers, [year])

    # C. 回傳地圖與自定義圖例
    # --------------------------------------------------
    with solara.Column():
        # 顯示地圖
        m.element()
        
        # 自定義 HTML 圖例 (比 geemap widget 更穩定)
        with solara.Card(style={"position": "absolute", "bottom": "20px", "right": "20px", "z-index": "1000", "width": "250px", "background-color": "rgba(255,255,255,0.8)"}):
            solara.Markdown("**NDCI 葉綠素濃度**")
            # CSS 漸層色條
            solara.HTML(tag="div", style="height: 20px; width: 100%; background: linear-gradient(to right, blue, white, green, yellow, red); margin-bottom: 5px; border: 1px solid #ccc;")
            # 數值標籤
            with solara.Row(justify="space-between"):
                solara.Text("-0.1 (清澈)", style="font-size: 12px")
                solara.Text("0.5 (優養)", style="font-size: 12px")

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        
        with solara.Column(align="center"):
            solara.Markdown("## 危害澎湖珊瑚礁之各項因子")
            with solara.Column(style={"max-width": "800px"}):
                solara.Markdown(
                    """
                    珊瑚礁生態系統面臨多重威脅，包括氣候變遷引發的海水溫度上升、海洋酸化、海水優樣化，以及人類活動如過度捕撈、污染和沿海開發等。
                    """
                )
            solara.Markdown("---")

        solara.Markdown("## 1. 海溫分布變化")
        solara.Markdown("---")

        solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
        
        with solara.Column(style={"max-width": "900px", "margin": "0 auto"}):
            solara.Markdown("""
            ### 優養化（Eutrophication）
            我們使用 Sentinel-2 衛星影像計算 **NDCI 指標** 來評估葉綠素濃度。
            (紅色區域代表潛在的藻類爆發風險)
            """)
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            
            # 載入地圖組件
            MapComponent(selected_year.value)

        solara.Markdown("---")
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown("預留空間")
        solara.Markdown("---")
        solara.Markdown("## 4. 人類活動影響")
        solara.Markdown("預留空間")