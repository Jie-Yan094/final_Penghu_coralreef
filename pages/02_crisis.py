import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
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
# 2. 地圖組件 (Colab 移植 Pro 版)
# ==========================================
@solara.component
def MapComponent(year):
    
    def get_map_html():
        # 1. 初始化地圖 (Folium)
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        
        # 2. 定義 ROI (使用您 Colab 的精確座標)
        roi = ee.Geometry.Rectangle([119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108])

        # 3. 定義時間：鎖定在該年份的「5月到9月」 (夏季藻類好發期)
        start_date = f'{year}-05-01'
        end_date = f'{year}-09-30'

        # 4. 定義 SCL 去雲函式 (移植自您的 Colab)
        def mask_s2_clouds_scl(image):
            scl = image.select('SCL')
            # 只保留數值為 6 (Water) 的像素
            mask = scl.eq(6)
            return image.updateMask(mask).divide(10000)

        # 5. 定義指數計算函式
        def add_indices(image):
            ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')
            return image.addBands(ndci)

        # 6. 影像集合處理 (邏輯完全比照 Colab)
        s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
              .filterDate(start_date, end_date)
              .filterBounds(roi)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) # 初步過濾
              .map(mask_s2_clouds_scl) # 精細去雲 (只留水體)
              .map(add_indices))       # 計算 NDCI

        # 取中位數合成 (因為已經限定夏季，這代表夏季平均狀態)
        image_median = s2.median().clip(roi)

        # 7. 視覺化參數 (比照 Colab 設定)
        # 注意：Colab 的顏色代碼沒加 #，這裡補上 # 以確保網頁渲染正確
        ndci_vis = {
            'min': -0.05, 
            'max': 0.15,
            'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']
        }
        
        # 8. 加入圖層
        try:
            # 真實色彩 (底圖)
            m.addLayer(image_median, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3}, 'True Color')
            
            # NDCI 分析圖層
            m.addLayer(image_median.select('NDCI'), ndci_vis, 'NDCI (Cleaned)')
            
            # Colorbar
            m.add_colorbar(
                colors=['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000'], 
                vmin=-0.05, 
                vmax=0.15, 
                label="NDCI Chlorophyll Index"
            )
        except Exception as e:
            print(f"圖層加入失敗: {e}")
            
        # 9. 生成 HTML (使用暫存檔解決權限問題)
        try:
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                temp_path = tmp.name
            
            m.to_html(filename=temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            os.remove(temp_path)
            return html_content
            
        except Exception as e:
            return f"<div>地圖生成錯誤: {str(e)}</div>"

    # 使用 use_memo
    map_html = solara.use_memo(get_map_html, dependencies=[year])

    # 10. 顯示 Iframe
    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "700px",
            "style": "border: none; display: block;" 
        }
    )

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        
        solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
        solara.Markdown("夏季 (5月-9月) 平均狀態，使用 SCL 波段排除非水體干擾。")
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            MapComponent(selected_year.value)