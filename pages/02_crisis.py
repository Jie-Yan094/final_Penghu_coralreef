import solara
import geemap  # 回歸 geemap，它是 GEE 的原廠工具，對圖層支援最好
import ee
import os
import json
from google.oauth2.service_account import Credentials

# 訊息顯示
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
# 2. 地圖生產函數 (Geemap 極簡模式)
# ==========================================
def get_map(year_val):
    # 建立地圖：關閉所有可能導致崩潰的互動工具
    # zoom=12 是澎湖的最佳視角
    m = geemap.Map(
        center=[23.5, 119.5], 
        zoom=12,
        toolbar_ctrl=False,  # 關工具列
        draw_ctrl=False,     # 關繪圖
        search_ctrl=False,   # 關搜尋
        layer_ctrl=True,     # 只留圖層控制
        scale_ctrl=True,     # 只留比例尺
        fullscreen_ctrl=False,
        attribution_ctrl=False
    )
    
    # 加入混合底圖 (衛星+路網)
    m.add_basemap("HYBRID")

    roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
    start_date = f'{year_val}-01-01'
    end_date = f'{year_val}-12-31'
    
    try:
        # 1. 抓取影像 (不設雲量限制，確保有圖)
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date))

        count = collection.size().getInfo()
        print(f"🔍 {year_val} 年共找到 {count} 張影像") # Log 確認點
        
        if count == 0:
            error_msg.set(f"❌ {year_val} 年無影像")
            return m

        # 2. 運算
        image = collection.median().clip(roi)
        ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')

        # 3. 視覺化參數
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': ['blue', 'white', 'green', 'yellow', 'red']}
        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

        # 4. 加入圖層 (geemap 會自動處理 Token 和 URL)
        m.addLayer(image, rgb_vis, f"{year_val} 真實色彩")
        m.addLayer(ndci, ndci_vis, f"{year_val} NDCI 指標")
        
        # 加上色標
        m.add_colorbar(vis_params=ndci_vis, label="NDCI")

        # 【強制視角】最後再鎖定一次，確保不會跑回全球
        m.setCenter(119.5, 23.5, 12)
        
        # 成功訊息
        error_msg.set("")
        info_msg.set(f"✅ {year_val} 年載入成功 (共 {count} 張合成)")
        
        # 【除錯用】印出其中一個圖層的網址，確認是否生成
        try:
             url = image.getMapId(rgb_vis)['tile_fetcher'].url_format
             print(f"🔗 產生的圖層網址範例: {url}")
        except:
             pass
        
    except Exception as e:
        error_msg.set(f"載入失敗: {str(e)}")
        print(f"❌ 詳細錯誤: {e}")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # CSS 強制修復版面
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

        # 地圖容器
        with solara.Column(style={"width": "100%", "height": "650px", "border": "1px solid #ddd", "margin-top": "20px"}):
            m = get_map(selected_year.value)
            # 使用 .element() 顯示
            m.element()
            
        with solara.Row(justify="center", style={"margin-top": "20px"}):
             solara.Markdown("---")