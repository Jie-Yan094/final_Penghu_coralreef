import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
import pandas as pd
import plotly.graph_objects as go
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
# 1. 變數與資料定義
# ==========================================
sst_year = solara.reactive(2024)      # 海溫年份
sst_type = solara.reactive("夏季均溫") # 海溫統計類型
selected_year = solara.reactive(2025) # NDCI 年份

# 寫死 NDCI 統計數據 (2016-2025) 供圖表使用
ndci_data = {
    'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'NDCI_Mean': [-0.059707, -0.064990, -0.063422, 0.041270, 0.041549, 
                  0.041954, 0.093461, 0.107500, 0.108534, 0.066040],
    'Image_Count': [24, 25, 52, 24, 30, 25, 23, 25, 19, 31]
}
df_ndci = pd.DataFrame(ndci_data)

# ==========================================
# 2. 地圖組件 A：海溫地圖 (SST)
# ==========================================

    "@solara.component
def SSTMap(year, period_type):""
    顯示 JAXA GCOM-C 衛星的海溫 (支援切換 全年/夏季)
    """
    def get_sst_map_html():
        m = geemap.Map(center=[23.5, 119.5], zoom=10)
        roi = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])

        # 根據使用者選擇的類型設定時間範圍
        if period_type == "夏季均溫":
            # 珊瑚白化好發期 (6月-9月)
            start_date = f'{year}-06-01'
            end_date = f'{year}-09-30'
            vis_min = 25 # 夏季溫度較高，拉高 min 讓對比更明顯
            vis_max = 33
            layer_title = f"{year} 夏季均溫 (6-9月)"
        else:
            # 全年平均
            start_date = f'{year}-01-01'
            end_date = f'{year}-12-31'
            vis_min = 15 # 全年包含冬天，min 要低一點
            vis_max = 32
            layer_title = f"{year} 全年平均"

        try:
            # JAXA GCOM-C 數據
            img_collection = (
                ee.ImageCollection('JAXA/GCOM-C/L3/OCEAN/SST/V3')
                .filterBounds(roi)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.eq('SATELLITE_DIRECTION', 'D')) # 只取白天
            )

            count = img_collection.size().getInfo()
            if count == 0:
                return f"<div style='padding:20px;'>無 {year} 年的 JAXA SST 數據 (資料通常始於 2018)</div>"

            # 使用中位數合成
            my_img_composite = img_collection.median().clip(roi)

            # 數值轉換 SST [°C] = SST_AVE * 0.0012 + (-10)
            dataset = my_img_composite.select('SST_AVE').multiply(0.0012).add(-10)

            # 可視化參數 (動態調整 min/max)
            sst_vis = {
              "bands": ['SST_AVE'],
              "min": vis_min, 
              "max": vis_max,
              "palette": ['000000', '005aff', '43c8c8', 'fff700', 'ff0000']
            }

            m.addLayer(dataset, sst_vis, layer_title)
            m.add_colorbar(sst_vis, label="海面溫度 (°C)", orientation='horizontal', layer_name=layer_title)

        except Exception as e:
            print(f"SST Map Error: {e}")
            return f"<div>SST 地圖載入失敗: {e}</div>"

        # 生成 HTML
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

    map_html = solara.use_memo(get_sst_map_html, dependencies=[year, period_type])

    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "600px",
            "style": "border: none; display: block; width: 100%;" 
        }
    )

# ==========================================
# 3. 地圖組件 B：優養化地圖 (NDCI)
# ==========================================
@solara.component
def NDCIMap(year):
    """
    這張地圖專注於顯示 Sentinel-2 的優養化/葉綠素指標
    """
    def get_ndci_map_html():
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        roi = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])
        start_date = f'{year}-05-01'
        end_date = f'{year}-09-30'

        # 雙模式去雲邏輯
        if year >= 2019:
            collection_name = 'COPERNICUS/S2_SR_HARMONIZED'
            def mask_algo(image):
                scl = image.select('SCL')
                mask = scl.eq(6) 
                return image.updateMask(mask).divide(10000)
        else:
            collection_name = 'COPERNICUS/S2_HARMONIZED'
            def mask_algo(image):
                qa = image.select('QA60')
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                qa_mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                ndwi = image.normalizedDifference(['B3', 'B8'])
                water_mask = ndwi.gt(0) 
                final_mask = qa_mask.And(water_mask)
                return image.updateMask(final_mask).divide(10000)

        def add_indices(image):
            ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')
            return image.addBands(ndci)

        s2 = (ee.ImageCollection(collection_name)
              .filterDate(start_date, end_date)
              .filterBounds(roi)
              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
              .map(mask_algo)
              .map(add_indices))

        image_median = s2.median().clip(roi)
        ndci_vis = {'min': -0.05, 'max': 0.15, 'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']}
        
        try:
            m.addLayer(image_median, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3}, 'True Color')
            layer_name = 'NDCI (Chlorophyll)'
            m.addLayer(image_median.select('NDCI'), ndci_vis, layer_name)
            m.add_colorbar(ndci_vis, label="NDCI Chlorophyll Index", layer_name=layer_name)
        except Exception as e:
            print(f"NDCI圖層加入失敗: {e}")
            
        # 生成 HTML
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

    map_html = solara.use_memo(get_ndci_map_html, dependencies=[year])

    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "600px",
            "style": "border: none; display: block; width: 100%;" 
        }
    )

# ==========================================
# 4. 地圖組件 C：棘冠海星警戒地圖 (Starfish)
# ==========================================
@solara.component
def StarfishMap():
    """
    這張地圖專門用來標示棘冠海星爆發的紅色警戒區
    """
    def get_starfish_map_html():
        m = geemap.Map(center=[23.35, 119.55], zoom=11)
        m.add_basemap("HYBRID") 

        qimei = ee.Geometry.Rectangle([119.408, 23.185, 119.445, 23.215])       
        dongji = ee.Geometry.Rectangle([119.658, 23.250, 119.680, 23.265])      
        xiji = ee.Geometry.Rectangle([119.605, 23.245, 119.625, 23.260])        
        dongyuping = ee.Geometry.Rectangle([119.510, 23.255, 119.525, 23.268])  
        xiyuping = ee.Geometry.Rectangle([119.500, 23.260, 119.510, 23.272])    

        outbreak_zones = ee.FeatureCollection([
            ee.Feature(qimei, {'name': '七美嶼'}),
            ee.Feature(dongji, {'name': '東吉嶼'}),
            ee.Feature(xiji, {'name': '西吉嶼'}),
            ee.Feature(dongyuping, {'name': '東嶼坪'}),
            ee.Feature(xiyuping, {'name': '西嶼坪'})
        ])
        
        style_params = {'color': 'red', 'width': 3, 'fillColor': '00000000'}

        try:
            m.addLayer(outbreak_zones.style(**style_params), {}, "棘冠海星爆發警戒區")
        except Exception as e:
            print(f"警戒區圖層加入失敗: {e}")

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

    map_html = solara.use_memo(get_starfish_map_html, dependencies=[])

    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "500px",
            "style": "border: none; display: block; width: 100%;" 
        }
    )

# ==========================================
# 5. 圖表組件：NDCI 統計圖 (已包含 titlefont 修正)
# ==========================================
@solara.component
def NDCIChart():
    with solara.Card("📊 歷年 NDCI 統計數據 (2016-2025)"):
        # 建立雙軸圖表
        fig = go.Figure()

        # 左軸：NDCI 折線圖
        fig.add_trace(go.Scatter(
            x=df_ndci['Year'], 
            y=df_ndci['NDCI_Mean'], 
            name='NDCI Mean',
            mode='lines+markers',
            line=dict(color='#00CC96', width=3),
            marker=dict(size=8)
        ))

        # 右軸：影像數量 長條圖
        fig.add_trace(go.Bar(
            x=df_ndci['Year'], 
            y=df_ndci['Image_Count'], 
            name='Image Count',
            marker_color='#636EFA',
            opacity=0.3,
            yaxis='y2'
        ))

        fig.update_layout(
            title='NDCI 夏季平均值 vs 有效影像數量',
            xaxis=dict(title='年份', tickmode='linear'),
            # 修正：titlefont 改為 title=dict(font=...)
            yaxis=dict(
                title=dict(text='NDCI 指數', font=dict(color="#00CC96")),
                tickfont=dict(color="#00CC96")
            ),
            yaxis2=dict(
                title=dict(text='影像數量 (張)', font=dict(color="#636EFA")),
                tickfont=dict(color="#636EFA"),
                overlaying='y',
                side='right'
            ),
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified",
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        solara.FigurePlotly(fig)
        
        solara.Markdown("""
        **數據解讀注意：** 2016-2018 (TOA) 與 2019-2025 (SR) 因衛星資料源校正方式不同，數值基準有差異。
        需關注的是 **2022年後 NDCI 顯著升高的趨勢**。
        """, style="font-size: 0.9em; color: gray;")

# ==========================================
# 6. 頁面組件 (排版整合)
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}, align="center"):
        
        with solara.Column(style={"max-width": "1000px", "width": "100%"}):
            solara.Markdown("# 危害澎湖珊瑚礁之各項因子")
            
            # ==========================================
            # 1. 海溫分布變化 (SST)
            # ==========================================
            solara.Markdown("---")
            solara.Markdown("## 1. 海溫分布變化 (Sea Surface Temperature)")
            
            solara.Markdown("""
            珊瑚對水溫非常敏感。長期的異常高溫（超過 30°C）會導致珊瑚白化甚至死亡。
            **夏季均溫**更能反映出珊瑚面臨的熱緊迫壓力。
            """)

            with solara.Card("🌡️ JAXA 衛星海溫監測"):
                with solara.Row(style={"align-items": "center", "gap": "20px"}):
                    # 1. 年份滑桿
                    with solara.Column(style={"flex-grow": "1"}):
                         solara.SliderInt(label="選擇年份", value=sst_year, min=2018, max=2025)
                    
                    # 2. 類型切換按鈕 (已修正為 ToggleButtonsSingle)
                    with solara.Column():
                        solara.ToggleButtonsSingle(value=sst_type, values=["全年平均", "夏季均溫"])

                solara.Markdown(f"### 📅 目前顯示：{sst_year.value} 年 - {sst_type.value}")

                # 呼叫海溫地圖組件
                SSTMap(sst_year.value, sst_type.value)
            
            solara.Markdown("---")
            
            # ==========================================
            # 2. 優養化 (NDCI)
            # ==========================================
            solara.Markdown("## 2. 海洋優養化指標 (NDCI)")
            
            solara.Markdown("""
            ### 優養化（Eutrophication）
            * 🔵 **藍色**：水質清澈
            * 🔴 **紅色**：優養化風險高 (藻類/葉綠素濃度高)
            """)
            
            solara.Markdown(f"### 夏季 (5月-9月) 平均狀態")
            if selected_year.value < 2019:
                solara.Markdown("*(年份 < 2019：使用 TOA 資料 + NDWI 去除陸地)*", style="font-size: 12px; color: gray;")
            else:
                solara.Markdown("*(年份 ≥ 2019：使用 SR 資料 + SCL 精準去陸地)*", style="font-size: 12px; color: green;")

            with solara.Column(style={"width": "100%", "padding-top": "20px"}):
                # 地圖區塊
                with solara.Card("Sentinel-2 衛星葉綠素監測"):
                    solara.SliderInt(label="選擇年份", value=selected_year, min=2016, max=2025)
                    NDCIMap(selected_year.value)
                
                # 統計圖表區塊
                solara.Markdown("<br>")
                NDCIChart()

            # ==========================================
            # 3. 棘冠海星
            # ==========================================
            with solara.Column(style={"width": "100%", "padding-top": "40px"}):
                solara.Markdown("---")
                solara.Markdown("## 3. 珊瑚礁生態系崩壞：棘冠海星的威脅")
                
                image_url = "https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg"
                
                with solara.Row(gap="24px", style={"flex-wrap": "wrap", "align-items": "center"}):
                    
                    # 左邊：圖片區塊
                    with solara.Div(style={
                        "flex": "1 1 400px", 
                        "min-width": "300px",
                        "overflow": "hidden",
                        "border-radius": "12px", 
                        "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.15)", 
                        "text-align": "center",
                        "padding": "0", 
                        "background-color": "#ffffff"
                    }):
                        solara.Image(image_url, width="100%")
                    
                    # 右邊：文字區塊
                    with solara.Div(style={"flex": "1 1 400px", "min-width": "300px"}):
                        solara.Markdown("""
                        ### 🌊 好餓好餓的珊瑚礁大胃王--棘冠海星(Crown-of-thorns Starfish)
                        近年來，澎湖海域傳出**棘冠海星**（俗稱魔鬼海星）異常增生的警訊。這種海星以珊瑚為食，當數量過多時，會對珊瑚礁生態系造成嚴重破壞，導致珊瑚覆蓋率大幅下降，生態平衡面臨威脅。
                        
                        **⚠️ 澎湖海域現況**：
                        除了**七美**海域外，南方四島國家公園範圍內的**東吉、西吉、東嶼坪、西嶼坪**等地區也觀察到棘冠海星數量激增，對當地珊瑚礁造成嚴重威脅。
                        """)
                
                # 地圖 B：棘冠海星警戒區
                with solara.Column(style={"width": "100%", "padding-top": "10px"}):
                     with solara.Card("⚠️ 棘冠海星爆發熱點地圖"):
                        solara.Markdown("**🟥 紅色框線標示出近期棘冠海星數量激增的區域 (七美及南方四島)**")
                        StarfishMap()

                with solara.Card("🔍 認識棘冠海星"):
                    solara.Markdown("""
                    * 棘冠海星是珊瑚礁生態系中的一員，但當牠們數量失控時，便會成為生態殺手。
                    * **🍽️ 專吃珊瑚**：牠們喜愛攝食成長快速的石珊瑚，會將胃翻出體外直接消化珊瑚蟲，留下一片慘白的珊瑚骨骼。
                    * **📈 食量驚人**：一隻成體在一年內，最多可吞噬高達 **6 平方公尺** 的珊瑚。
                    * **⚠️ 具毒性**：體表布滿尖銳的毒棘，人類若不慎觸碰可能會中毒受傷。
                    * **🥚 繁殖力強**：產卵量巨大，這使得牠們在環境條件合適時，極容易迅速擴散。
                    """)

                solara.Markdown("### 🚨 為什麼會失控？大爆發的原因")
                solara.Markdown("目前科學界認為是多重因素的綜合結果：")
                
                with solara.Row():
                    with solara.Column():
                        solara.Info("**1. 營養鹽增加 (優養化)**\n人類排放的污水導致海水氮、磷增加，促使浮游植物大量繁殖。這提供了棘冠海星幼體充足的食物，大幅提高存活率。")
                        solara.Info("**2. 天敵數量減少**\n大法螺、蘇眉魚等天敵因過度捕撈而減少，失去了制衡力量。")
                        solara.Info("**3. 氣候變遷**\n海洋暖化有利於幼生發育，寒害則可能導致捕食牠們的魚群死亡。")
                    
                    with solara.Column():
                        solara.Info("**4. 自然週期性波動**\n即使無人為干擾，海星族群也可能每隔數十年自然爆發一次。")
                        solara.Info("**5. 海流擴散**\n海流能將大量的幼生帶往新的珊瑚礁區。")
                        solara.Info("**6. 驚人的繁殖力**\n只要抓到一次機會，就能以幾何級數增長。")

                solara.Markdown("### 📊 監測紀錄與警訊")
                solara.Markdown("""
                * **澳洲大堡礁**：過去 27 年的研究顯示，珊瑚覆蓋率下降的主因中，**棘冠海星的啃食佔了 42%**，破壞力僅次於颱風。
                * **澎湖海域**：近年來，澎湖七美、東吉、西吉、東嶼坪、西嶼坪等地區也觀察到棘冠海星數量激增，對當地珊瑚礁造成嚴重威脅。
                > **生態平衡的警戒線**：每公頃超過 **30隻** 棘冠海星，即視為爆發警戒。
                """)
                solara.Markdown("---")

            # ==========================================
            # 4. 人類活動
            # ==========================================
            solara.Markdown("## 4. 人類活動影響")
            solara.Markdown("*(預留空間)*")

            # ==========================================
            # 5. 參考資料
            # ==========================================
            solara.Markdown("## 5. 參考資料")
            solara.Markdown("""
            * 1.開放博物館．棘寥之海：從棘冠海星看見生態的臨界點．https://openmuseum.tw/muse/exhibition/403675c2280b4d08a8c7c19ab71f51e1#imgs-gghuozn6go
            * 2.海巡署全球資訊網．澎湖西吉島海域棘冠海星大爆發事件與控管．https://www.cga.gov.tw/GipOpen/wSite/public/Attachment/f1294389984406.pdf
            * 3.自然保育與環境資訊基金會．2024 澎湖南方四島-東西嶼坪珊瑚礁體檢成果報告．https://tnf.org.tw/archives/35245
            """)