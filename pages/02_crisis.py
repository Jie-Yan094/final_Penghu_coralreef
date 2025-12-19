import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile  # 【新增】用於處理暫存檔
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
# 2. 地圖組件 (Folium HTML + TempFile 修復版)
# ==========================================
@solara.component
def MapComponent(year):
    
    def get_map_html():
        # 1. 初始化地圖 (Folium)
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

        ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')
        
        ndwi = collection.normalizedDifference(['B3', 'B8'])
        water_mask = ndwi.gt(0)
        ndci_masked = ndci.updateMask(water_mask)

        ndci_vis = {
            'min': -0.1, 
            'max': 0.5, 
            'palette': ['blue', 'white', 'green', 'yellow', 'red']
        }
        
        # 3. 加入圖層
        try:
            m.addLayer(collection, {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}, 'True Color')
            m.addLayer(ndci_masked, ndci_vis, 'NDCI')
            m.add_colorbar(
                colors=['blue', 'white', 'green', 'yellow', 'red'], 
                vmin=-0.1, 
                vmax=0.5, 
                label="NDCI Chlorophyll"
            )
        except Exception as e:
            print(f"圖層加入失敗: {e}")
            
        # 4. 【關鍵修復】使用系統暫存區來生成 HTML
        # 使用 tempfile 確保我們有權限寫入，且檔名不會衝突
        try:
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                temp_path = tmp.name
            
            # 將地圖存入暫存路徑
            m.to_html(filename=temp_path)
            
            # 讀取暫存檔內容
            with open(temp_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # (選用) 讀完後刪除暫存檔以節省空間
            os.remove(temp_path)
            
            return html_content
            
        except Exception as e:
            return f"<div>地圖生成錯誤: {str(e)}</div>"

    # 使用 use_memo 緩存 HTML
    map_html = solara.use_memo(get_map_html, dependencies=[year])

    # 5. 顯示
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
        solara.Markdown("紅色區域代表優養化風險高，藍色區域則為低風險。請選擇年份以查看不同年度的狀況。")
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            MapComponent(selected_year.value)