import solara
import geemap  # 【修改 1】改用 geemap，它對 GEE 的支援度最好
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
# 2. 地圖生產函數 (使用 geemap 優化版)
# ==========================================
def get_final_map(year_val):
    # 【修改 2】使用 geemap.Map
    m = geemap.Map(center=[23.5, 119.5], zoom=11)
    # 設定底圖，HYBRID 對於觀察沿岸特徵比較清楚
    m.add_basemap("HYBRID")

    roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
    start_date = f'{year_val}-01-01'
    end_date = f'{year_val}-12-31'
    
    # 獲取影像集合
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(roi)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                  .median()
                  .clip(roi)) # 在這裡先 Clip，後續計算比較乾淨

    # 計算 NDCI (Normalized Difference Chlorophyll Index)
    # 公式: (RedEdge1 - Red) / (RedEdge1 + Red) -> (B5 - B4) / (B5 + B4)
    ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')

    # 【優化】簡單的水體遮罩 (選擇性)：利用 NDWI 把陸地遮掉，讓 NDCI 只顯示在海面上
    # NDWI = (Green - NIR) / (Green + NIR) -> (B3 - B8) / (B3 + B8)
    ndwi = collection.normalizedDifference(['B3', 'B8'])
    water_mask = ndwi.gt(0) # NDWI > 0 視為水體
    ndci_masked = ndci.updateMask(water_mask)

    # 視覺化參數 (使用 Hex code 比較保險)
    # 藍色(低葉綠素) -> 白色 -> 綠色 -> 黃色 -> 紅色(高葉綠素/優養化)
    palette = ['#0000ff', '#ffffff', '#00ff00', '#ffff00', '#ff0000']
    
    ndci_vis = {
        'min': -0.1, 
        'max': 0.5, 
        'palette': palette
    }
    
    rgb_vis = {
        'min': 0, 
        'max': 3000, 
        'bands': ['B4', 'B3', 'B2']
    }

    try:
        # 【修改 3】使用 geemap 的 addLayer
        m.addLayer(collection, rgb_vis, f"{year_val} 真實色彩 (RGB)")
        m.addLayer(ndci_masked, ndci_vis, f"{year_val} 葉綠素指標 (NDCI)")
        
        # 【修改 4】加入 Colorbar (geemap 的寫法)
        m.add_colorbar_branca(
            colors=palette, 
            vmin=-0.1, 
            vmax=0.5, 
            label="NDCI 葉綠素濃度 (優養化程度)"
        )
        
        # 自動縮放到 ROI
        m.centerObject(roi, 11)
        
    except Exception as e:
        print(f"圖層載入警告: {e}")
    
    return m

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
            我們使用 Sentinel-2 衛星影像計算 **NDCI 指標** (Normalized Difference Chlorophyll Index) 來評估葉綠素濃度：
            * 🔵 **藍色**：水質清澈 (低葉綠素)。
            * 🟢 **綠色**：正常浮游生物量。
            * 🔴 **紅色**：優養化風險高 (藻類爆發)。
            *(註：已自動遮罩陸地範圍)*
            """)
        
        # 地圖區塊
        with solara.Card("Sentinel-2 衛星葉綠素監測"):
            solara.SliderInt(label="選擇年份", value=selected_year, min=2019, max=2024) 
            # Sentinel-2 資料通常從 2015 後半開始，建議 slider 從 2016 或 2019 開始比較完整
            
            # 呼叫地圖函數
            m = get_final_map(selected_year.value)
            
            # 顯示地圖
            # geemap 物件在 solara 中也是 ipywidget，直接用 element() 渲染
            m.element(height="700px")

        solara.Markdown("---")
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown("預留空間")
        solara.Markdown("---")
        solara.Markdown("## 4. 人類活動影響")
        solara.Markdown("預留空間")