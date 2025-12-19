import solara
import leafmap
import ee
import os
import json
from google.oauth2.service_account import Credentials

# ==========================================
# 0. GEE 驗證與初始化 (已確認 OK)
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
# 2. 地圖生產函數 (功能完整版)
# ==========================================
def get_final_map(year_val):
    # 建立地圖，直接鎖定澎湖，Zoom 設為 11 比較剛好
    m = leafmap.Map(center=[23.5, 119.5], zoom=11)
    m.add_basemap("HYBRID")

    roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
    start_date = f'{year_val}-01-01'
    end_date = f'{year_val}-12-31'
    
    # 為了確保有畫面，雲量維持 30%
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(roi)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                  .median())

    ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')

    palette = ['blue', 'white', 'green', 'yellow', 'red']
    ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
    rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

    try:
        m.add_ee_layer(collection.clip(roi), rgb_vis, f"{year_val} 真實色彩")
        m.add_ee_layer(ndci.clip(roi), ndci_vis, f"{year_val} 葉綠素(優養化)指標")
        m.add_colorbar(colors=palette, vmin=-0.1, vmax=0.5, label="NDCI (葉綠素濃度)")
    except Exception as e:
        print(f"圖層載入警告: {e}")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # 主容器：拿掉 align="center"，避免地圖被擠扁
    with solara.Column(style={"width": "100%", "padding": "20px"}):
        
        # 標題區塊 (這裡可以置中)
        with solara.Column(align="center"):
            solara.Markdown("## 危害澎湖珊瑚礁之各項因子")
            with solara.Column(style={"max-width": "800px"}):
                solara.Markdown(
                    """
                    珊瑚礁生態系統面臨多重威脅，包括氣候變遷引發的海水溫度上升、海洋酸化、海水優樣化，以及人類活動如過度捕撈、污染和沿海開發等。這些因子不僅削弱了珊瑚的健康，還影響了整個生態系統的穩定性與生物多樣性。了解並減緩這些威脅對於保護澎湖珊瑚礁及其豐富的海洋生態至關重要。
                    """
                )
            solara.Markdown("---")

        # --- 1. 海溫區塊 ---
        solara.Markdown("## 1. 海溫分布變化")
        solara.Markdown("---")

        # --- 2. 優養化區塊 ---
        solara.Markdown("## 2. 海洋優養化指標")
        
        # 文字說明區
        with solara.Column(style={"max-width": "900px", "margin": "0 auto"}): # 讓文字區塊居中就好
            solara.Markdown("""
            ### 優養化（Eutrophication）
            通常意味著水中的營養鹽過多，這會導致藻類爆發。對於珊瑚礁來說，這是一個巨大的威脅，因為：
            * **競爭光線**：過多的浮游藻類會讓海水變混濁，擋住陽光。
            * **空間競爭**：大型藻類會長得比珊瑚快，直接覆蓋珊瑚。
            """)
            
            solara.Markdown("""
            我們使用 Sentinel-2 衛星影像計算 **NDCI 指標** 來評估葉綠素濃度：
            * 🔵 **藍色**：水質清澈。
            * 🟢 **綠色**：正常浮游生物量。
            * 🔴 **紅色**：優養化風險高。
            """)
        
        # 地圖區塊 (獨立出來，確保寬度足夠)
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2015, max=2024)
            
            m = get_final_map(selected_year.value)
            
            # 【關鍵修正】這裡不設 width="100%"，而是直接讓它自然撐開，或者給一個響應式樣式
            # 為了保險，我們給它一個 min-width
            solara.Markdown("載入地圖中...") # 提示文字
            m.element(height="700px")

        solara.Markdown("---")

        # --- 其他區塊 ---
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown("預留空間")
        solara.Markdown("---")
        solara.Markdown("## 4. 人類活動影響")
        solara.Markdown("預留空間")
        solara.Markdown("---")