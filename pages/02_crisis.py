import solara
import leafmap.leafmap as leafmap
import ee
import os
import json
from google.oauth2.service_account import Credentials

# 訊息變數
error_msg = solara.reactive("")
info_msg = solara.reactive("")

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
selected_year = solara.reactive(2023)

# ==========================================
# 2. 地圖生產函數 (改用 getMapId 直通法)
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
                      .filterDate(start_date, end_date))

        count = collection.size().getInfo()
        print(f"🔍 {year_val} 年共找到 {count} 張影像")
        
        if count == 0:
            error_msg.set(f"❌ {year_val} 年無影像")
            return m

        # 2. 取中位數運算
        image = collection.median().clip(roi)
        ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')

        # 3. 設定視覺化參數
        palette = ['blue', 'white', 'green', 'yellow', 'red']
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

        # 【關鍵修改】手動索取 MapID (繞過 add_ee_layer 的 bug)
        # 這會直接向 Google 要一個網址，而不是讓 Python 套件去轉譯
        
        # A. 真實色彩圖層
        map_id_rgb = image.getMapId(rgb_vis)
        tile_url_rgb = map_id_rgb['tile_fetcher'].url_format
        m.add_tile_layer(url=tile_url_rgb, name=f"{year_val} 真實色彩", attribution="Google Earth Engine")

        # B. NDCI 優養化圖層
        map_id_ndci = ndci.getMapId(ndci_vis)
        tile_url_ndci = map_id_ndci['tile_fetcher'].url_format
        m.add_tile_layer(url=tile_url_ndci, name=f"{year_val} 葉綠素(優養化)指標", attribution="Google Earth Engine")

        # 加上色標 (這是純 UI，不會影響圖層)
        m.add_colorbar(colors=palette, vmin=-0.1, vmax=0.5, label="NDCI")
        
        # 4. 強制視角
        m.set_center(119.5, 23.5, 12)
        
        # 成功訊息
        error_msg.set("")
        info_msg.set(f"✅ 成功載入 {year_val} 年 (共 {count} 張合成)")
        
    except Exception as e:
        error_msg.set(f"載入失敗: {str(e)}")
        print(f"❌ 詳細錯誤: {e}")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    solara.Style("""
        .jupyter-widgets { width: 100% !important; }
        .leaflet-container { width: 100% !important; height: 100% !important; }
    """)

    with solara.Column(style={"width": "100%", "padding-bottom": "50px"}):
        
        with solara.Row(justify="center"):
            with solara.Column(style={"max-width": "800px"}):
                solara.Markdown("## 危害澎湖珊瑚礁之各項因子")
                solara.Markdown("---")
                solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
                
                if error_msg.value:
                    solara.Error(error_msg.value)
                if info_msg.value:
                    solara.Success(info_msg.value)

        solara.Markdown("### Sentinel-2 衛星監測地圖")
        
        with solara.Row(justify="center"):
            with solara.Column(style={"width": "300px"}):
                solara.SliderInt(label="選擇年份", value=selected_year, min=2017, max=2024)

        with solara.Column(style={"width": "100%", "height": "650px", "border": "1px solid #ddd", "margin-top": "20px"}):
            m = get_map(selected_year.value)
            m.element()
            
        with solara.Row(justify="center", style={"margin-top": "20px"}):
             solara.Markdown("---")