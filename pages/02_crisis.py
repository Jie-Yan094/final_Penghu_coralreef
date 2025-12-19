import solara
import geemap.foliumap as geemap  # 【關鍵】改用 foliumap，不依賴 WebSocket
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
selected_year = solara.reactive(2021)

# ==========================================
# 2. 地圖組件 (Folium HTML 版 - 絕對穩定)
# ==========================================
@solara.component
def MapComponent(year):
    
    # 建立地圖函數
    def get_map_html():
        # 1. 初始化地圖 (使用 foliumap)
        # 這裡產生的不是 Widget，而是靜態的地圖物件，中心點寫死在裡面
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        
        # 2. GEE 資料處理
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

        # 視覺參數
        ndci_vis = {
            'min': -0.1, 
            'max': 0.5, 
            'palette': ['blue', 'white', 'green', 'yellow', 'red']
        }
        
        # 3. 加入圖層
        try:
            m.addLayer(collection, {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}, 'True Color')
            m.addLayer(ndci_masked, ndci_vis, 'NDCI')
            
            # 加入 Colorbar (foliumap 的 colorbar 比較穩定)
            m.add_colorbar(
                colors=['blue', 'white', 'green', 'yellow', 'red'], 
                vmin=-0.1, 
                vmax=0.5, 
                label="NDCI Chlorophyll"
            )
        except Exception as e:
            print(f"圖層加入失敗: {e}")
            
        # 4. 轉為 HTML 字串
        return m.to_html()

    # 使用 use_memo 只有在年份改變時才重新生成 HTML
    # 這會讓地圖在切換年份時閃一下，但保證位置正確
    map_html = solara.use_memo(get_map_html, dependencies=[year])

    # 5. 使用 Iframe 顯示
    # 這是最暴力的解法：直接把生成的 HTML 塞進一個框架裡
    # 這樣 Solara 就管不到地圖內部，地圖也不會被 Solara 的佈局影響
    return solara.components.html.Iframe(
        src_doc=map_html,
        width="100%",
        height="700px"
    )

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        
        solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
        solara.Markdown("紅色區域代表優養化風險高。")
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            
            # 呼叫地圖
            MapComponent(selected_year.value)