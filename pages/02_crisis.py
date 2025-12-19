import solara
import ipyleaflet
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
# 2. 地圖生產函數
# ==========================================
def get_map(year_val):
    # 定義澎湖的邊界 (南, 西, 北, 東)
    # fit_bounds 是比 center 更強制的定位方式
    bounds = ((23.1, 119.3), (23.8, 119.8))
    
    m = ipyleaflet.Map(
        center=[23.5, 119.5], 
        zoom=11, # 稍微拉遠一點點確保看得到全貌
        scroll_wheel_zoom=True
    )
    
    # 加入圖層控制器
    m.add_control(ipyleaflet.LayersControl(position='topright'))

    # 強制鎖定視角 (雙重保險)
    m.fit_bounds(bounds)

    roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
    start_date = f'{year_val}-01-01'
    end_date = f'{year_val}-12-31'
    
    try:
        # 1. GEE 影像運算
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date))

        count = collection.size().getInfo()
        print(f"🔍 {year_val} 年共找到 {count} 張影像")
        
        if count == 0:
            error_msg.set(f"❌ {year_val} 年無影像")
            return m

        # 2. 取中位數
        image = collection.median().clip(roi)
        ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')

        # 3. 設定參數
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': ['blue', 'white', 'green', 'yellow', 'red']}
        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

        # ======================================================
        # 手動取得 MapID
        # ======================================================
        
        # A. 真實色彩 (底圖)
        map_id_rgb = image.getMapId(rgb_vis)
        layer_rgb = ipyleaflet.TileLayer(
            url=map_id_rgb['tile_fetcher'].url_format, 
            name=f"{year_val} 真實色彩",
            attribution="Google Earth Engine"
        )
        m.add_layer(layer_rgb)

        # B. NDCI 優養化指標 (上層)
        map_id_ndci = ndci.getMapId(ndci_vis)
        layer_ndci = ipyleaflet.TileLayer(
            url=map_id_ndci['tile_fetcher'].url_format, 
            name=f"{year_val} NDCI 指標",
            attribution="Google Earth Engine"
        )
        m.add_layer(layer_ndci)

        # 成功訊息
        error_msg.set("")
        info_msg.set(f"✅ {year_val} 年載入成功 (共 {count} 張合成)")
        
    except Exception as e:
        error_msg.set(f"載入失敗: {str(e)}")
        print(f"❌ 詳細錯誤: {e}")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # CSS 確保地圖滿版
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
            
            # 【絕對關鍵】這裡加了 key，強迫 Solara 每次年份改變時，把舊地圖徹底銷毀
            # 這能解決地圖 "卡在非洲" 或 "不更新" 的所有問題
            with solara.Column(key=f"map-container-{selected_year.value}"):
                m = get_map(selected_year.value)
                m.element()
        
        # 色標
        with solara.Row(justify="center", style={"margin-top": "10px"}):
            solara.Markdown("**色標說明：** 🔵 藍色(低濃度/清澈) ➝ ⚪ 白色 ➝ 🟢 綠色 ➝ 🟡 黃色 ➝ 🔴 紅色(高濃度/優養化)")
            
        with solara.Row(justify="center", style={"margin-top": "20px"}):
             solara.Markdown("---")