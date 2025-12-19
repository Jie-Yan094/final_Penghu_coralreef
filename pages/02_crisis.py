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
# 2. 地圖組件 (圖例修復版)
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
                
                # 2. 使用 NDWI 去除陸地 (NDWI > 0 為水體)
                ndwi = image.normalizedDifference(['B3', 'B8'])
                water_mask = ndwi.gt(0) 
                
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

        # 6. 視覺化參數 (定義一次，重複使用)
        ndci_vis = {
            'min': -0.05, 
            'max': 0.15,
            'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']
        }
        
        # 7. 加入圖層與圖例
        try:
            m.addLayer(image_median, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3}, 'True Color')
            
            # 加入 NDCI 圖層
            layer_name = 'NDCI (Chlorophyll)'
            m.addLayer(image_median.select('NDCI'), ndci_vis, layer_name)
            
            # 【關鍵修復】
            # 直接傳入 ndci_vis 字典，並指定 layer_name，這樣 geemap 才能正確綁定參數
            m.add_colorbar(
                ndci_vis, 
                label="NDCI Chlorophyll Index", 
                layer_name=layer_name
            )
            
        except Exception as e:
            print(f"圖層/圖例加入失敗: {e}")
            
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

    # 9. 顯示 Iframe (寬度設定為 100%)
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
    with solara.Column(style={"width": "100%", "padding": "20px"}, align="center"):
        
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("# 危害澎湖珊瑚礁之各項因子")
            solara.Markdown("---")
            solara.Markdown("## 1. 海溫分布變化")
            solara.Markdown("*(預留海溫分析內容)*")
            solara.Markdown("---")
            solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
            
            solara.Markdown("""
            ### 優養化（Eutrophication）
            * 🔵 **藍色**：水質清澈
            * 🔴 **紅色**：優養化風險高
            """)
            
            solara.Markdown(f"### 夏季 (5月-9月) 平均狀態")
            if selected_year.value < 2019:
                solara.Markdown("*(年份 < 2019：使用 TOA 資料 + NDWI 去除陸地)*", style="font-size: 12px; color: gray;")
            else:
                solara.Markdown("*(年份 ≥ 2019：使用 SR 資料 + SCL 精準去陸地)*", style="font-size: 12px; color: green;")

        # 地圖區塊
        with solara.Column(style={"width": "100%", "padding-top": "20px"}):
            with solara.Card("Sentinel-2 衛星葉綠素監測"):
                solara.SliderInt(label="選擇年份", value=selected_year, min=2016, max=2025)
                MapComponent(selected_year.value)
        
        with solara.Column(style={"max-width": "900px", "width": "100%", "padding-top": "20px"}):
            solara.Markdown("---")

        # ----------------------------------------------------
        # 3. 珊瑚礁生態系崩壞 (加入棘冠海星內容)
        # ----------------------------------------------------
        with solara.Column(style={"max-width": "900px", "width": "100%", "padding-top": "40px"}):
            solara.Markdown("---")
            solara.Markdown("## 3. 珊瑚礁生態系崩壞：棘冠海星的威脅")
            
            solara.Markdown("""
            ### 🌊 珊瑚礁大胃王:棘冠海星 (Crown-of-thorns Starfish) 
            近年來，澎湖七美、西吉嶼等海域傳出**棘冠海星**（俗稱魔鬼海星）異常增生的警訊。這些被稱為「魔鬼海星」的生物，正悄悄啃食著我們美麗的珊瑚礁。
            """)

            with solara.Card("🔍 認識棘冠海星"):
                solara.Markdown("""
                棘冠海星本是珊瑚礁生態系中的一員，但當牠們數量失控時，便會成為生態殺手。
                * **🍽️ 專吃珊瑚**：牠們喜愛攝食成長快速的石珊瑚，會將胃翻出體外直接消化珊瑚蟲，留下一片慘白的珊瑚骨骼。
                * **📈 食量驚人**：一隻成體在一年內，最多可吞噬高達 **6 平方公尺** 的珊瑚。
                * **⚠️ 具毒性**：體表布滿尖銳的毒棘，人類若不慎觸碰可能會中毒受傷。
                * **🥚 繁殖力強**：產卵量巨大，這使得牠們在環境條件合適時，極容易迅速擴散。
                """)

            solara.Markdown("### 🚨 為什麼會失控？大爆發的原因")
            solara.Markdown("目前科學界認為是多重因素的綜合結果：")
            
            with solara.Row():
                with solara.Column():
                    solara.Info("""
                    **1. 營養鹽增加 (優養化)**
                    人類排放的污水導致海水氮、磷增加，促使浮游植物大量繁殖。這提供了棘冠海星幼體充足的食物，大幅提高存活率。
                    """)
                    solara.Info("""
                    **2. 天敵數量減少**
                    大法螺、蘇眉魚等天敵因過度捕撈而減少，失去了制衡力量。 
                    """)
                    solara.Info("""
                    **3. 氣候變遷**
                    海洋暖化有利於幼生發育，寒害則可能導致捕食牠們的魚群死亡。
                    """)
                
                with solara.Column():
                    solara.Info("""
                    **4. 自然週期性波動**
                    即使無人為干擾，海星族群也可能每隔數十年自然爆發一次。
                    """)
                    solara.Info("""
                    **5. 海流擴散**
                    海流能將大量的幼生帶往新的珊瑚礁區。
                    """)
                    solara.Info("""
                    **6. 驚人的繁殖力**
                    只要抓到一次機會，就能以幾何級數增長。
                    """)

            solara.Markdown("### 📊 對珊瑚礁生態系的重要性")
            solara.Markdown("""
            * **澳洲大堡礁**：過去 27 年的研究顯示，珊瑚覆蓋率下降的主因中，**棘冠海星的啃食佔了 42%**，破壞力僅次於颱風。
            * **澎湖海域**：近年來，澎湖七美、東吉、西吉、東嶼坪、西嶼坪等地區也觀察到棘冠海星數量激增，對當地珊瑚礁造成嚴重威脅。
            """)
            
            solara.Markdown("""
            > **生態平衡的警戒線**：每公頃超過 **30隻** 棘冠海星，即視為爆發警戒。
            """)

            solara.Markdown("---")
            solara.Markdown("## 4. 人類活動影響")
            solara.Markdown("預留空間")
