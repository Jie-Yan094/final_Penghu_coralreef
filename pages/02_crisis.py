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
selected_year = solara.reactive(2024)

# ==========================================
# 2. 地圖組件 (穩定版：Folium + 雙演算法切換)
# ==========================================
@solara.component
def MapComponent(year):
    
    def get_map_html():
        # 1. 初始化地圖 (使用 foliumap 避免崩潰)
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        
        # 2. 定義 ROI (您指定的精確座標)
        roi = ee.Geometry.Rectangle([119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108])

        # 3. 定義夏季時間 (藻類好發期)
        start_date = f'{year}-05-01'
        end_date = f'{year}-09-30'

        # =========================================
        # 🔥 核心邏輯：依照年份自動切換演算法
        # =========================================
        if year >= 2019:
            # --- 現代 Pro 版 (2019-2025) ---
            # 使用 L2A (SR) 資料 + SCL 強力去雲 (只留水體)
            collection_name = 'COPERNICUS/S2_SR_HARMONIZED'
            
            def mask_algo(image):
                scl = image.select('SCL')
                # 6 = Water (精準水體)
                mask = scl.eq(6) 
                return image.updateMask(mask).divide(10000)
                
        else:
            # --- 懷舊通用版 (2015-2018) ---
            # 使用 L1C (TOA) 資料 + QA60 基本去雲
            collection_name = 'COPERNICUS/S2_HARMONIZED'
            
            def mask_algo(image):
                qa = image.select('QA60')
                # Bit 10: Opaque clouds, Bit 11: Cirrus clouds
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
                       qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                return image.updateMask(mask).divide(10000)

        # 4. 指數計算 (NDCI)
        def add_indices(image):
            ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')
            return image.addBands(ndci)

        # 5. 影像處理管線
        s2 = (ee.ImageCollection(collection_name)
              .filterDate(start_date, end_date)
              .filterBounds(roi)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) # 初步篩選
              .map(mask_algo)  # 自動選用對應去雲法
              .map(add_indices))

        # 取中位數合成 (夏季平均)
        image_median = s2.median().clip(roi)

        # 6. 視覺化參數 (比照 Colab 靈敏度)
        ndci_vis = {
            'min': -0.05, 
            'max': 0.15,
            'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']
        }
        
        # 7. 加入圖層
        try:
            # 底圖：真實色彩
            m.addLayer(image_median, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3}, 'True Color')
            
            # 分析圖：NDCI
            m.addLayer(image_median.select('NDCI'), ndci_vis, 'NDCI (Chlorophyll)')
            
            # 圖例：Colorbar (強制顯示)
            m.add_colorbar(
                colors=['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000'], 
                vmin=-0.05, 
                vmax=0.15, 
                label="NDCI Chlorophyll Index"
            )
        except Exception as e:
            print(f"圖層加入失敗: {e}")
            
        # 8. 生成 HTML (使用暫存檔繞過權限問題)
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

    # 使用 use_memo 緩存 HTML
    map_html = solara.use_memo(get_map_html, dependencies=[year])

    # 9. 顯示 Iframe
    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "700px",
            "style": "border: none; display: block; margin: 0 auto;" # margin auto 確保 iframe 本身也置中
        }
    )

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    # 主容器：全寬、內距、內容置中
    with solara.Column(style={"width": "100%", "padding": "20px"}, align="center"):
        
        # --- 標題區 ---
        with solara.Column(style={"max-width": "900px", "text-align": "center"}):
            solara.Markdown("# 危害澎湖珊瑚礁之各項因子")
            solara.Markdown("---")
        
        # --- 1. 海溫區塊 ---
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("## 1. 海溫分布變化")
            solara.Markdown("*(預留海溫分析內容)*")
            solara.Markdown("---")

        # --- 2. 優養化區塊 (主要功能) ---
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
            
            # 說明文字
            solara.Markdown("""
            ### 優養化（Eutrophication）
            水體中營養鹽過多導致藻類爆發，會遮蔽陽光並覆蓋珊瑚。
            """)
            
            # 圖例說明
            solara.Markdown("""
            **Sentinel-2 NDCI 指標判讀：**
            * 🔵 **藍色**：水質清澈
            * 🟢 **綠色**：正常
            * 🔴 **紅色**：優養化風險高 (藻類濃度高)
            """)
            
            # 資料源說明 (自動變換文字)
            solara.Markdown(f"### 夏季 (5月-9月) 平均狀態")
            if selected_year.value < 2019:
                solara.Markdown("*(年份 < 2019：自動切換為 L1C 資料，精度較低)*", style="font-size: 12px; color: gray;")
            else:
                solara.Markdown("*(年份 ≥ 2019：使用 SR 資料 + SCL 高精度去雲，只保留純淨水體)*", style="font-size: 12px; color: green;")

        # 地圖區塊
        with solara.Column(style={"max-width": "1000px", "width": "100%", "align-items": "center"}):
            with solara.Card("Sentinel-2 衛星葉綠素監測"):
                # Slider (範圍開到 2016)
                solara.SliderInt(label="選擇年份", value=selected_year, min=2016, max=2024)
                # Map
                MapComponent(selected_year.value)
        
        solara.Markdown("---")

        # --- 3. 珊瑚礁生態系崩壞區塊 ---
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("## 3. 珊瑚礁生態系崩壞")
            solara.Markdown("預留空間")
            solara.Markdown("---")

        # --- 4. 人類活動影響區塊 ---
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("## 4. 人類活動影響")
            solara.Markdown("預留空間")