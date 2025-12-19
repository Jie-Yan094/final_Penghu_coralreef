import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
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
selected_year = solara.reactive(2025)

# ==========================================
# 2. 地圖組件 (寬度修復 + 全年份陸地遮罩)
# ==========================================
@solara.component
def MapComponent(year):
    
    def get_map_html():
        # 1. 初始化地圖
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        
        # 2. 定義 ROI
        roi = ee.Geometry.Rectangle([119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108])

        # 3. 定義夏季時間
        start_date = f'{year}-05-01'
        end_date = f'{year}-09-30'

        # =========================================
        # 🔥 核心邏輯：雙模式去雲與去陸地
        # =========================================
        if year >= 2019:
            # --- 2019 後：SR 資料 + SCL 強力遮罩 ---
            collection_name = 'COPERNICUS/S2_SR_HARMONIZED'
            
            def mask_algo(image):
                scl = image.select('SCL')
                mask = scl.eq(6) # 6 = Water (精確水體)
                return image.updateMask(mask).divide(10000)
                
        else:
            # --- 2018 前：TOA 資料 + NDWI 替代遮罩 ---
            collection_name = 'COPERNICUS/S2_HARMONIZED'
            
            def mask_algo(image):
                # 1. 基本 QA60 去雲
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                qa_mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
                          qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                
                # 2. 【新增】使用 NDWI 去除陸地 (NDWI > 0 為水體)
                ndwi = image.normalizedDifference(['B3', 'B8'])
                water_mask = ndwi.gt(0) 
                
                # 結合兩個遮罩
                final_mask = qa_mask.And(water_mask)
                
                return image.updateMask(final_mask).divide(10000)

        # 4. 指數計算
        def add_indices(image):
            ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')
            return image.addBands(ndci)

        # 5. 影像處理
        s2 = (ee.ImageCollection(collection_name)
              .filterDate(start_date, end_date)
              .filterBounds(roi)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
              .map(mask_algo)
              .map(add_indices))

        image_median = s2.median().clip(roi)

        # 6. 視覺化參數
        ndci_vis = {
            'min': -0.05, 
            'max': 0.15,
            'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']
        }
        
        # 7. 加入圖層
        try:
            m.addLayer(image_median, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3}, 'True Color')
            m.addLayer(image_median.select('NDCI'), ndci_vis, 'NDCI (Chlorophyll)')
            m.add_colorbar(
                colors=['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000'], 
                vmin=-0.05, vmax=0.15, label="NDCI Chlorophyll Index"
            )
        except Exception as e:
            print(f"圖層加入失敗: {e}")
            
        # 8. 生成 HTML
        try:
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                temp_path = tmp.name
            m.to_html(filename=temp_path)
            with open(temp_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            os.remove(temp_path)
            return html_content
        except Exception as e:
            return f"<div>地圖生成錯誤: {str(e)}</div>"

    map_html = solara.use_memo(get_map_html, dependencies=[year])

    # 9. 顯示 Iframe (寬度修復：width=100%)
    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "700px",
            "style": "border: none; display: block; width: 100%;" 
        }
    )

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # 主容器：保持 align="center" 讓文字置中，但透過內部寬度控制讓地圖撐開
    with solara.Column(style={"width": "100%", "padding": "20px"}, align="center"):
        
        # --- 標題與文字區 (限制寬度以利閱讀) ---
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("# 危害澎湖珊瑚礁之各項因子")
            solara.Markdown("---")
            solara.Markdown("## 1. 海溫分布變化")
            solara.Markdown("*(預留海溫分析內容)*")
            solara.Markdown("---")
            solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
            
            solara.Markdown("""
            ### 優養化（Eutrophication）
            水體中營養鹽過多導致藻類爆發，會遮蔽陽光並覆蓋珊瑚。
            * 🔵 **藍色**：水質清澈
            * 🔴 **紅色**：優養化風險高 (藻類濃度高)
            """)
            
            solara.Markdown(f"### 夏季 (5月-9月) 平均狀態")
            if selected_year.value < 2019:
                solara.Markdown("*(年份 < 2019：使用 TOA 資料 + NDWI 去除陸地)*", style="font-size: 12px; color: gray;")
            else:
                solara.Markdown("*(年份 ≥ 2019：使用 SR 資料 + SCL 精準去陸地)*", style="font-size: 12px; color: green;")

        # --- 地圖區塊 (放寬寬度限制，解決被擠扁的問題) ---
        # 這裡不限制 max-width，或者設得很大，確保地圖能橫向展開
        with solara.Column(style={"width": "100%", "padding-top": "20px"}):
            with solara.Card("Sentinel-2 衛星葉綠素監測"):
                # Slider
                solara.SliderInt(label="選擇年份", value=selected_year, min=2016, max=2024)
                # Map (現在應該會撐滿卡片)
                MapComponent(selected_year.value)
        
        # --- 底部文字區 ---
        with solara.Column(style={"max-width": "900px", "width": "100%", "padding-top": "20px"}):
            solara.Markdown("---")
            solara.Markdown("## 3. 珊瑚礁生態系崩壞")
            solara.Markdown("預留空間")
            solara.Markdown("---")
            solara.Markdown("## 4. 人類活動影響")
            solara.Markdown("預留空間")