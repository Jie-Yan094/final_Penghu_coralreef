import solara
import ipyleaflet
import geemap
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
# 2. 地圖組件 (視角強制修正版)
# ==========================================
@solara.component
def MapComponent(year):
    # --- A. 初始化地圖 ---
    def init_map():
        # 建立地圖實例
        m = ipyleaflet.Map(
            center=[23.5, 119.5],  # 初始中心
            zoom=11,               # 初始縮放
            scroll_wheel_zoom=True,
            layout={'height': '700px'}
        )
        
        # 加入衛星底圖 (使用最穩定的加入方式)
        try:
            # 嘗試加入 ESRI 衛星圖
            esri_layer = ipyleaflet.Basemap.to_layer(ipyleaflet.basemaps.Esri.WorldImagery)
            m.add_layer(esri_layer)
            
            # 嘗試加入地名標籤
            label_layer = ipyleaflet.Basemap.to_layer(ipyleaflet.basemaps.CartoDB.PositronOnlyLabels)
            m.add_layer(label_layer)
        except:
            # 如果失敗，至少加入一個標準底圖
            m.add_layer(ipyleaflet.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"))

        return m

    # 使用 use_memo 鎖定地圖物件，防止閃退
    m = solara.use_memo(init_map, dependencies=[])

    # --- B. 定義「強制回到澎湖」的動作 ---
    def fly_to_penghu():
        m.center = [23.5, 119.5]
        m.zoom = 11

    # --- C. 更新圖層與視角 ---
    def update_layers():
        # 1. 強制設定視角 (解決地圖跑掉、中心錯誤的關鍵!)
        # 每次年份改變或初始化時，都強制把鏡頭拉回澎湖
        fly_to_penghu()

        # 2. 清理舊圖層 (保留底圖)
        # 假設前兩層是底圖與標籤，我們從 index 2 開始切掉
        if len(m.layers) > 2:
            m.layers = m.layers[:2]

        # 3. GEE 資料處理
        roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'

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

        ndci_vis = {
            'min': -0.1, 
            'max': 0.5, 
            'palette': ['#0000ff', '#ffffff', '#00ff00', '#ffff00', '#ff0000']
        }
        
        # 4. 加入圖層
        try:
            # 使用 geemap 轉換 GEE 影像為 TileLayer
            layer = geemap.ee_tile_layer(ndci_masked, ndci_vis, name=f"{year} NDCI")
            m.add_layer(layer)
            print(f"✅ 圖層已加入: {year}")
        except Exception as e:
            print(f"❌ 圖層加入失敗: {e}")

    # 當年份改變時，執行 update_layers
    solara.use_effect(update_layers, [year])

    # --- D. 畫面渲染 ---
    with solara.Column():
        # 地圖本體
        m.element()
        
        # 【新功能】手動重置按鈕 (如果地圖還是跑掉，按這個救命)
        with solara.Div(style="position: absolute; top: 80px; left: 60px; z-index: 1000;"):
            solara.Button("📍 回到澎湖視角", on_click=fly_to_penghu, color="primary")

        # 圖例 (Legend)
        with solara.Card(style="position: absolute; bottom: 20px; right: 20px; z-index: 1000; width: 250px; background-color: rgba(255,255,255,0.9);"):
            solara.Markdown("**NDCI 葉綠素濃度**")
            solara.HTML(tag="div", style="height: 20px; width: 100%; background: linear-gradient(to right, blue, white, green, yellow, red); margin-bottom: 5px; border: 1px solid #ccc;")
            with solara.Row(justify="space-between"):
                solara.Text("-0.1 (清澈)", style="font-size: 12px")
                solara.Text("0.5 (優養)", style="font-size: 12px")

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
        
        with solara.Column(style={"max-width": "900px", "margin": "0 auto"}):
            solara.Markdown("紅色區域代表優養化風險高 (藻類濃度高)。")
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            # 載入地圖
            MapComponent(selected_year.value)