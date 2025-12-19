import solara
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
# 2. 地圖組件 (穩定版)
# ==========================================
@solara.component
def MapComponent(year):
    # --- A. 初始化地圖 (只執行一次) ---
    def init_map_once():
        # 【關鍵修正】關閉 toolbar_ctrl 和 draw_ctrl 以避免 Widget Closed Error
        m = geemap.Map(
            center=[23.5, 119.5], 
            zoom=11, 
            height="700px",
            toolbar_ctrl=False,  # 關閉工具列 (解決報錯的核心)
            draw_ctrl=False,     # 關閉繪圖工具
            data_ctrl=False      # 關閉資料工具
        )
        m.add_basemap("HYBRID")
        
        # 【優化】Colorbar 是固定的，在這裡加一次就好，不要在迴圈裡重複加
        palette = ['#0000ff', '#ffffff', '#00ff00', '#ffff00', '#ff0000']
        
        # 使用 branca colorbar (HTML based) 比較穩定
        m.add_colorbar_branca(
            colors=palette, 
            vmin=-0.1, 
            vmax=0.5, 
            label="NDCI 葉綠素濃度 (優養化程度)"
        )
        return m

    # 使用 use_memo 確保地圖物件不會被重複建立
    m = solara.use_memo(init_map_once, dependencies=[])

    # --- B. 更新圖層 (當 year 改變時執行) ---
    def update_layers():
        if m is None: return
        
        # 1. 清理舊圖層
        # m.layers[0] 是底圖，我們保留它，移除後面的所有疊加層
        if len(m.layers) > 1:
            m.layers = m.layers[:1]
        
        # 2. 定義 ROI 與 時間
        roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
        
        # 3. 獲取影像與計算
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                      .median()
                      .clip(roi))

        ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')
        
        # 水體遮罩
        ndwi = collection.normalizedDifference(['B3', 'B8'])
        water_mask = ndwi.gt(0)
        ndci_masked = ndci.updateMask(water_mask)

        # 視覺參數
        palette = ['#0000ff', '#ffffff', '#00ff00', '#ffff00', '#ff0000']
        ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
        rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}
        
        try:
            # 4. 加入新圖層
            m.addLayer(collection, rgb_vis, f"{year} 真實色彩")
            m.addLayer(ndci_masked, ndci_vis, f"{year} 葉綠素指標")
            
        except Exception as e:
            print(f"圖層更新錯誤: {e}")

    # 註冊副作用，當 year 變動時觸發 update_layers
    solara.use_effect(update_layers, [year])

    # 回傳地圖元素
    return m.element(height="700px")

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        
        with solara.Column(align="center"):
            solara.Markdown("## 危害澎湖珊瑚礁之各項因子")
            with solara.Column(style={"max-width": "800px"}):
                solara.Markdown(
                    """
                    珊瑚礁生態系統面臨多重威脅，包括氣候變遷引發的海水溫度上升、海洋酸化、海水優樣化，以及人類活動如過度捕撈、污染和沿海開發等。
                    """
                )
            solara.Markdown("---")

        solara.Markdown("## 1. 海溫分布變化")
        solara.Markdown("---")

        solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
        
        with solara.Column(style={"max-width": "900px", "margin": "0 auto"}):
            solara.Markdown("""
            ### 優養化（Eutrophication）
            我們使用 Sentinel-2 衛星影像計算 **NDCI 指標** 來評估葉綠素濃度：
            * 🔵 **藍色**：水質清澈。
            * 🔴 **紅色**：優養化風險高。
            """)
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024)
            
            # 呼叫地圖組件
            MapComponent(selected_year.value)

        solara.Markdown("---")
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown("預留空間")
        solara.Markdown("---")
        solara.Markdown("## 4. 人類活動影響")
        solara.Markdown("預留空間")