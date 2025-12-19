import solara
import leafmap.leafmap as leafmap
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
        # 本機測試用
        ee.Initialize(project='ee-s1243037-0')
        print("⚠️ 本機環境：使用預設驗證")
except Exception as e:
    print(f"❌ GEE 初始化失敗: {e}")

# ==========================================
# 1. 變數定義
# ==========================================
selected_year = solara.reactive(2025)

# ==========================================
# 2. 地圖生產函數 (Function Pattern)
# ==========================================
def get_eutrophication_map(year_val):
    """
    建立並回傳一個設定好的 leafmap.Map 物件
    """
    m = leafmap.Map(center=[23.5, 119.5], zoom=11)
    m.add_basemap("HYBRID")

    roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
    start_date = f'{year_val}-01-01'
    end_date = f'{year_val}-12-31'
    
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(roi)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                  .median())

    ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')

    palette = ['blue', 'white', 'green', 'yellow', 'red']
    ndci_vis = {'min': -0.1, 'max': 0.5, 'palette': palette}
    rgb_vis = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

    m.add_ee_layer(collection.clip(roi), rgb_vis, f"{year_val} 真實色彩")
    m.add_ee_layer(ndci.clip(roi), ndci_vis, f"{year_val} 葉綠素(優養化)指標")
    
    m.add_colorbar(colors=palette, vmin=-0.1, vmax=0.5, label="NDCI (葉綠素濃度)")
    
    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    
    with solara.Column(align="center", style={"text-align": "center", "width": "100%"}):
        
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
        # (這裡未來可以放海溫地圖)

        solara.Markdown("---")

        # --- 2. 優養化區塊 (已合併你的新文字) ---
        solara.Markdown("## 2. 海洋優養化指標")
        
        # 這裡放入你提供的說明文字，我微調了 Markdown 符號讓排版更漂亮
        with solara.Column(style={"max-width": "800px", "text-align": "left"}):
            solara.Markdown("""
            ### 優養化（Eutrophication）
            通常意味著水中的營養鹽過多，這會導致藻類爆發（Algae Bloom）。對於珊瑚礁來說，這是一個巨大的威脅，因為：
            * **競爭光線**：過多的浮游藻類會讓海水變混濁，擋住陽光，共生藻無法行光合作用。
            * **空間競爭**：大型藻類會長得比珊瑚快，直接覆蓋並「悶死」珊瑚。
            """)
            
            solara.Markdown("""
            為了監測澎湖海域的優養化情況，我們使用了 Sentinel-2 衛星影像，並計算了 **NDCI（Normalized Difference Chlorophyll Index）** 指標。
            NDCI 是一種用於評估水體中葉綠素濃度的指標，葉綠素濃度高通常意味著水中營養鹽豐富，可能導致優養化現象。
            """)
        
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            # 這裡放入顏色說明
            solara.Markdown("""
            **透過 NDCI 指標分析澎湖海域葉綠素濃度：**
            * 🔵 **藍色**：水質清澈，葉綠素濃度低。
            * 🟢 **綠色**：正常的浮游生物量。
            * 🔴 **紅色**：葉綠素濃度異常高，可能有優養化或藻華現象，或者是靠近岸邊的懸浮物質較多。
            """)
            
            # 滑桿
            solara.SliderInt(label="選擇年份", value=selected_year, min=2015, max=2025)
            
            # 顯示地圖 (使用函數模式，穩定不報錯)
            m = get_eutrophication_map(selected_year.value)
            m.element(height="600px", width="100%")

        solara.Markdown("---")

        # --- 3. 珊瑚礁生態系崩壞區塊 ---
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown("等一下我再來寫這裡")
        solara.Markdown("---")

        # --- 4. 人類活動影響 ---
        solara.Markdown("## 4. 人類活動影響-海洋垃圾")
        solara.Markdown("這裡也等一下我再來寫")
        solara.Markdown("---")