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
# 2. 地圖組件 (修正版)
# ==========================================
@solara.component
def MapComponent(year):
    # 【關鍵修正 1】使用 use_memo 確保 Map 只被初始化一次
    # dependencies=[] 表示這個 map 物件永遠不會被重建，除非頁面完全重整
    m = solara.use_memo(
        lambda: geemap.Map(center=[23.5, 119.5], zoom=11, height="700px"),
        dependencies=[]
    )

    # 【關鍵修正 2】使用 use_effect 來處理圖層更新
    # 當 [year, m] 發生變化時，執行此函數
    def update_layers():
        if m is None: return
        
        # 1. 清除舊的 GEE 圖層 (保留底圖)
        # 為了避免閃爍或錯誤，我們移除所有名稱不是 base layer 的圖層
        m.layers = m.layers[:1]  # 通常第0層是底圖，保留它，移除上面疊加的層
        
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
            
            # 5. 更新 Colorbar (先移除舊的以免重複堆疊)
            # geemap 的 colorbar 處理比較 tricky，最簡單的方式是先不重複加，或者清除 widget
            # 這裡我們嘗試重新加入
            m.clear_controls() # 清除舊的 controls (包含 colorbar)
            m.add_control(geemap.ZoomControl(position="topleft"))
            m.add_control(geemap.ScaleControl(position="bottomleft"))
            m.add_control(geemap.LayersControl(position="topright"))
            
            m.add_colorbar_branca(
                colors=palette, 
                vmin=-0.1, 
                vmax=0.5, 
                label="NDCI 葉綠素濃度"
            )
            
        except Exception as e:
            print(f"圖層更新錯誤: {e}")

    # 將 update_layers 註冊為 effect，當 year 改變時觸發
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
            
            # 這裡呼叫新的組件，而不是直接呼叫函數
            MapComponent(selected_year.value)

        solara.Markdown("---")
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown("預留空間")
        solara.Markdown("---")
        solara.Markdown("## 4. 人類活動影響")
        solara.Markdown("預留空間")