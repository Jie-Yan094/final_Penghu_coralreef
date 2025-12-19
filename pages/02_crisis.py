import solara
import leafmap
import ee
import os
import json
from google.oauth2.service_account import Credentials

# 錯誤訊息顯示變數
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
        # 【關鍵修正 1】移除雲量過濾
        # 我們不再篩選 filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        # 直接抓取該年「所有」影像，讓 median() 自動去雲
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date))

        # 【關鍵修正 2】檢查到底有沒有抓到圖 (會顯示在 logs)
        count = collection.size().getInfo()
        print(f"🔍 {year_val} 年共找到 {count} 張影像")
        
        if count == 0:
            error_msg.set(f"❌ {year_val} 年沒有找到任何影像，請嘗試其他年份")
            return m

        # 取中位數 (這一步會自動過濾掉移動的雲)
        image = collection.median()

        # 計算 NDCI
        ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')

        # 設定參數
        palette = ['blue', 'white', 'green', 'yellow', 'red']
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

        # 加入圖層
        m.add_ee_layer(image.clip(roi), rgb_vis, f"{year_val} 真實色彩")
        m.add_ee_layer(ndci.clip(roi), ndci_vis, f"{year_val} 葉綠素(優養化)指標")
        m.add_colorbar(colors=palette, vmin=-0.1, vmax=0.5, label="NDCI")
        
        # 強制視角
        m.set_center(119.5, 23.5, 12)
        
        # 成功訊息
        error_msg.set("")
        info_msg.set(f"✅ 成功載入 {year_val} 年影像 (共 {count} 張合成)")
        
    except Exception as e:
        error_msg.set(f"圖層載入失敗: {str(e)}")
        print(f"❌ 詳細錯誤: {e}")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # CSS 修正版面
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
                
                # 顯示狀態訊息
                if error_msg.value:
                    solara.Error(error_msg.value)
                if info_msg.value:
                    solara.Success(info_msg.value)

        solara.Markdown("### Sentinel-2 衛星監測地圖")
        
        with solara.Row(justify="center"):
            with solara.Column(style={"width": "300px"}):
                solara.SliderInt(label="選擇年份", value=selected_year, min=2017, max=2024) # S2 從 2017 開始比較穩

        # 地圖容器
        with solara.Column(style={"width": "100%", "height": "650px", "border": "1px solid #ddd", "margin-top": "20px"}):
            m = get_map(selected_year.value)
            m.element()
            
        with solara.Row(justify="center", style={"margin-top": "20px"}):
             solara.Markdown("---")