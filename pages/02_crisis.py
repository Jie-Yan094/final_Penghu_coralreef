import solara
import leafmap
import ee
import os
import json
from google.oauth2.service_account import Credentials

# 用來顯示錯誤訊息的變數
error_msg = solara.reactive("")

# ==========================================
# 0. GEE 驗證
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
# 【改回 2023】先用 2023 年，確保一定有完整資料，避免 2024/2025 資料不全導致空白
selected_year = solara.reactive(2023)

# ==========================================
# 2. 地圖生產函數
# ==========================================
def get_map(year_val):
    # 建立地圖
    m = leafmap.Map(center=[23.5, 119.5], zoom=12)
    m.add_basemap("HYBRID")

    roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
    start_date = f'{year_val}-01-01'
    end_date = f'{year_val}-12-31'
    
    try:
        # 1. 抓取影像
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                      .median())

        # 2. 計算 NDCI
        ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')

        # 3. 設定參數
        palette = ['blue', 'white', 'green', 'yellow', 'red']
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

        # 4. 加入圖層 (如果這裡失敗，會跳到 except)
        m.add_ee_layer(collection.clip(roi), rgb_vis, f"{year_val} 真實色彩")
        m.add_ee_layer(ndci.clip(roi), ndci_vis, f"{year_val} 葉綠素(優養化)指標")
        m.add_colorbar(colors=palette, vmin=-0.1, vmax=0.5, label="NDCI")
        
        # 5. 【強制視角】再次鎖定澎湖
        m.set_center(119.5, 23.5, 12)
        
        # 清除錯誤訊息
        error_msg.set("")
        
    except Exception as e:
        # 如果失敗，把錯誤顯示在網頁上
        error_msg.set(f"圖層載入失敗: {str(e)}")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # 注入 CSS 修復版面 (這是你那張成功截圖的關鍵)
    solara.Style("""
        .jupyter-widgets { width: 100% !important; }
        .leaflet-container { width: 100% !important; height: 100% !important; }
    """)

    with solara.Column(style={"width": "100%", "padding-bottom": "50px"}):
        
        # 標題區
        with solara.Row(justify="center"):
            with solara.Column(style={"max-width": "800px"}):
                solara.Markdown("## 危害澎湖珊瑚礁之各項因子")
                solara.Markdown("---")
                solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
                
                # 如果有錯誤，顯示紅字
                if error_msg.value:
                    solara.Error(error_msg.value)

        # 地圖區
        solara.Markdown("### Sentinel-2 衛星監測地圖")
        
        with solara.Row(justify="center"):
            with solara.Column(style={"width": "300px"}):
                solara.SliderInt(label="選擇年份", value=selected_year, min=2015, max=2024)

        # 地圖容器
        with solara.Column(style={"width": "100%", "height": "650px", "border": "1px solid #ddd", "margin-top": "20px"}):
            m = get_map(selected_year.value)
            m.element()
            
        with solara.Row(justify="center", style={"margin-top": "20px"}):
             solara.Markdown("---")