import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
from google.oauth2.service_account import Credentials

# ==========================================
# 0. 強健的 GEE 初始化
# ==========================================
def initialize_ee():
    try:
        token = os.environ.get('EARTHENGINE_TOKEN')
        if token:
            try:
                info = json.loads(token)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/earthengine'])
                ee.Initialize(credentials=creds, project='ee-s1243037-0')
                return "✅ 雲端認證成功"
            except Exception as json_err:
                return f"❌ JSON 格式錯誤: {json_err}"
        else:
            ee.Initialize(project='ee-s1243037-0')
            return "⚠️ 本機環境認證"
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        return f"❌ 系統崩潰: {e}"

init_status = initialize_ee()

# ==========================================
# 1. 響應式變數定義
# ==========================================
target_year = solara.reactive(2016)
smoothing_radius = solara.reactive(20) 

# ==========================================
# 2. 地圖組件：珊瑚礁棲地分類 (Benthic Habitat)
# ==========================================
@solara.component
def ReefClassificationMap(year, radius):
    def get_reef_map_html():
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        roi = ee.Geometry.Rectangle([119.2741, 23.1694, 119.8114, 23.8792])
        
        # B. 深度資料與遮罩
        depth_asset = ee.Image('projects/ee-s1243041/assets/bathymetry_0')
        actual_band = depth_asset.bandNames().get(0)
        depth_img = depth_asset.select([actual_band]).rename('depth').clip(roi)

        # ⭐ 修正：將 200 改為 2000 (20公尺)，解決大面積空洞問題
        depth_mask = depth_img.lt(2000).And(depth_img.gt(0))

        # C. 平滑化邏輯
        def smooth_logic(img_mask, r):
            return img_mask.focal_mode(radius=r, units='meters', kernelType='circle')

        # D. 訓練模型 (以 2018 年為準)
        img_2018 = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                    .filterBounds(roi)
                    .filterDate('2018-01-01', '2018-12-31')
                    .median().clip(roi).select('B.*'))
        
        mask_2018 = smooth_logic(img_2018.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), radius)
        water_2018 = img_2018.updateMask(mask_2018)
        
        my_benthic = ee.Image('ACA/reef_habitat/v2_0').clip(roi)
        classValues = [0, 11, 12, 13, 14, 15, 18]
        remapValues = ee.List.sequence(0, 6)
        label_img = my_benthic.remap(classValues, remapValues, bandName='benthic').rename('benthic').toByte()
        
        # 訓練樣本 (適度減少樣本點以加快渲染速度)
        training_samples = water_2018.addBands(label_img).stratifiedSample(
            numPoints=3000, classBand='benthic', region=roi, scale=10, geometries=True
        )
        classifier = ee.Classifier.smileRandomForest(100).train(training_samples, 'benthic', water_2018.bandNames())

        # E. 目標年份處理
        target_img = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                      .filterBounds(roi)
                      .filterDate(f'{year}-01-01', f'{year}-12-31')
                      .median().clip(roi).select('B.*'))
        
        mask_target = smooth_logic(target_img.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), radius)
        water_target = target_img.updateMask(mask_target)
        
        # 分類並套用眾數濾波 (再度平滑化結果)
        classified = water_target.classify(classifier).focal_mode(radius=radius, units='meters')

        # F. 可視化
        s2_vis = {'min': 100, 'max': 3500, 'bands': ['B4', 'B3', 'B2']}
        class_vis = {'min': 0, 'max': 6, 'palette': ['000000', 'ffffbe', 'e0d05e', 'b19c3a', '668438', 'ff6161', '9bcc4f']}
        
        m.addLayer(water_target, s2_vis, f"{year} Sentinel-2")
        m.addLayer(classified, class_vis, f"{year} 棲地分類結果")
        m.add_legend(title="棲地類別", keys=["無數據", "沙地", "沙/藻", "硬珊瑚", "軟珊瑚", "碎石", "海草"], colors=class_vis['palette'])
        
        return m.to_html()

    map_html = solara.use_memo(get_reef_map_html, dependencies=[year, radius])

    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "750px",
            "style": "border: none; border-radius: 8px;"
        }
    )

@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}, align="center"):
        with solara.Column(style={"max-width": "1000px", "width": "100%"}):
            solara.Markdown("# 澎湖底棲生物動態監測系統")
            solara.Markdown(f"**系統狀態**: {init_status}")
            
            solara.Markdown("""
            本系統結合 **Sentinel-2 衛星影像** 與 **隨機森林機器學習**。
            透過形態學濾波 (Morphological Filtering) 技術填補孔洞，使地圖分布更連續。
            """)

            with solara.Row(style={"gap": "20px"}):
                with solara.Column(style={"width": "350px"}):
                    with solara.Card("控制面板"):
                        solara.Markdown("#### 1. 時間維度")
                        solara.Select(label="選擇監測年份", value=target_year, 
                                      values=[2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
                        
                        solara.Markdown("---")
                        solara.Markdown("#### 2. 影像優化 (填補孔洞)")
                        solara.SliderInt(label="平滑半徑 (m)", value=smoothing_radius, min=0, max=80)
                        solara.Info(f"目前的半徑為 {smoothing_radius.value} 公尺。")

                with solara.Column(style={"flex": "1"}):
                    with solara.Card(f"📍 {target_year.value} 年 棲地分布圖"):
                        ReefClassificationMap(target_year.value, smoothing_radius.value)

            solara.Markdown("---")
            solara.Markdown("### 演算法說明：隨機森林監督式分類")
            solara.Markdown("利用 2018 年 ACA (Allen Coral Atlas) 數據作為地面真實標籤進行模型訓練，並應用於各年份之光譜影像。")

# 啟動 Page
Page()