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
# 2. 地圖組件 (強制重繪版)
# ==========================================
@solara.component
def MapWidget(year):
    """
    這個組件負責建立單一、靜態的地圖實例。
    我們不試圖更新它，而是依靠外層的 key 機制來重建它。
    """
    
    # 1. 準備 GEE 資料 (在建立地圖前先準備好)
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

    # 2. 建立地圖實例
    # 注意：這裡不再使用 use_memo，因為我們希望每次這個組件被 mount 時都是全新的
    m = ipyleaflet.Map(
        center=[23.5, 119.5],  # 這裡寫死澎湖座標
        zoom=11,
        basemap=ipyleaflet.basemaps.Esri.WorldImagery,
        scroll_wheel_zoom=True,
        layout={'height': '700px', 'width': '100%'}
    )

    # 3. 加入 GEE 圖層
    try:
        # 產生 TileLayer
        gee_layer = geemap.ee_tile_layer(ndci_masked, ndci_vis, name=f"{year} NDCI")
        m.add_layer(gee_layer)
        
        # 加入地名標籤 (選用)
        m.add_layer(ipyleaflet.Basemap.to_layer(ipyleaflet.basemaps.CartoDB.PositronOnlyLabels))
        
    except Exception as e:
        print(f"圖層載入錯誤: {e}")

    # 4. 回傳地圖元素
    return m.element()

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        
        solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
        
        with solara.Column(style={"max-width": "900px", "margin": "0 auto"}):
             solara.Markdown("""
            ### 優養化（Eutrophication）
            (紅色區域代表潛在的藻類爆發風險)
            """)
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            # Slider
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            
            # 【關鍵修改】
            # 我們在這裡呼叫 MapWidget，並且給它一個 key。
            # 當 selected_year.value 改變時，key 也會變 (例如 "map-2023" -> "map-2024")
            # Solara 會認為這是一個全新的組件，因此會銷毀舊的，建立一個全新的地圖。
            # 這樣保證了每次地圖出來時，中心點一定會重置到 [23.5, 119.5]。
            MapWidget(selected_year.value).key(f"map-{selected_year.value}")

            # 圖例 (Legend) - 獨立於地圖之外
            with solara.Div(style="margin-top: 10px; display: flex; justify-content: center;"):
                with solara.Card(style="width: 300px; padding: 10px; text-align: center;"):
                    solara.Text("NDCI 葉綠素濃度", style="font-weight: bold;")
                    solara.HTML(tag="div", style="height: 20px; width: 100%; background: linear-gradient(to right, blue, white, green, yellow, red); margin: 5px 0; border: 1px solid #ccc;")
                    with solara.Row(justify="space-between"):
                        solara.Text("-0.1 (清澈)")
                        solara.Text("0.5 (優養)")