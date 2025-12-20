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
def initialize_ee():
    try:
        key_content = os.environ.get('EARTHENGINE_TOKEN')
        if key_content:
            service_account_info = json.loads(key_content)
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(credentials=creds, project='ee-s1243037-0')
            return "✅ 雲端環境驗證成功"
        else:
            ee.Initialize(project='ee-s1243037-0')
            return "⚠️ 本機環境預設驗證"
    except Exception as e:
        return f"❌ 初始化失敗: {e}"

init_status = initialize_ee()

# ==========================================
# 1. 響應式變數定義
# ==========================================
target_year = solara.reactive(2016)
smoothing_radius = solara.reactive(20) # 解決孔洞問題的平滑半徑

# ==========================================
# 2. 地圖組件：珊瑚礁棲地分類 (Benthic Habitat)
# ==========================================
@solara.component
def ReefClassificationMap(year, radius):
    def get_reef_map_html():
        # A. 初始化地圖與 ROI
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        roi = ee.Geometry.Rectangle([119.2741, 23.1694, 119.8114, 23.8792])
        
        # B. 深度資料與遮罩 (解決深水區域錯誤分類問題)
        # 自動偵測波段名稱 (解決 b1 vs depth 的問題)
        depth_asset = ee.Image('projects/ee-s1243041/assets/bathymetry_0')
        actual_band = depth_asset.bandNames().get(0)
        depth_img = depth_asset.select([actual_band]).rename('depth').clip(roi)

        # 深度遮罩設定：0 < 深度 < 20 m
        depth_mask = depth_img.lt(200).And(depth_img.gt(0))

        # C. 平滑化邏輯 (解決影像中的椒鹽噪點與孔洞)
        def smooth_logic(img_mask, r):
            return img_mask.focal_mode(radius=r, units='meters', kernelType='circle')

        # D. 訓練模型 (以 2018 年作為標籤基準)
        img_2018 = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                    .filterBounds(roi)
                    .filterDate('2018-01-01', '2018-12-31')
                    .median().clip(roi).select('B.*'))
        
        # 建立 2018 遮罩並平滑
        mask_2018 = smooth_logic(img_2018.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), radius)
        water_2018 = img_2018.updateMask(mask_2018)
        
        # 載入 ACA 標籤並重新映射
        my_benthic = ee.Image('ACA/reef_habitat/v2_0').clip(roi)
        classValues = [0, 11, 12, 13, 14, 15, 18]
        remapValues = ee.List.sequence(0, 6)
        label_img = my_benthic.remap(classValues, remapValues, bandName='benthic').rename('benthic').toByte()
        
        # 訓練隨機森林
        training_samples = water_2018.addBands(label_img).stratifiedSample(
            numPoints=5000, classBand='benthic', region=roi, scale=10, geometries=True
        )
        classifier = ee.Classifier.smileRandomForest(100).train(training_samples, 'benthic', water_2018.bandNames())

        # E. 分類目標年份
        target_img = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                      .filterBounds(roi)
                      .filterDate(f'{year}-01-01', f'{year}-12-31')
                      .median().clip(roi).select('B.*'))
        
        # 建立目標年份遮罩並平滑
        mask_target = smooth_logic(target_img.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), radius)
        water_target = target_img.updateMask(mask_target)
        
        # 執行分類與結果後處理平滑
        classified = water_target.classify(classifier).focal_mode(radius=radius, units='meters')

        # F. 可視化設定
        s2_vis = {'min': 100, 'max': 3500, 'bands': ['B4', 'B3', 'B2']}
        class_vis = {'min': 0, 'max': 6, 'palette': ['000000', 'ffffbe', 'e0d05e', 'b19c3a', '668438', 'ff6161', '9bcc4f']}
        
        m.addLayer(water_target, s2_vis, f"{year} Sentinel-2")
        m.addLayer(classified, class_vis, f"{year} 棲地分類結果")
        m.add_legend(title="棲地類別", keys=["無數據", "沙地", "沙/藻混合", "硬珊瑚", "軟珊瑚", "碎石", "海草"], colors=class_vis['palette'])
        
        return m.to_html()

    # 使用 memo 優化效能，只有年份或半徑改變時才重算
    map_html = solara.use_memo(get_reef_map_html, dependencies=[year, radius])

    return solara.HTML(
        tag="iframe",
        attributes={
            "srcDoc": map_html,
            "width": "100%",
            "height": "750px",
            "style": "border: none; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
        }
    )




# ==========================================
# 頁面組件 (排版整合)
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px"}, align="center"):
        
        with solara.Column(style={"max-width": "900px", "width": "100%"}):
            solara.Markdown("# 澎湖底棲生物分類")
            with solara.Row(style={"justify-content": "space-between", "align-items": "center"}):
            #solara.Title("澎湖珊瑚礁棲地動態監測系統")
            #solara.Text(f"系統狀態: {init_status}", style={"font-size": "14px", "color": "#666"})
        
                solara.Markdown("""
        ### 系統說明
        本系統利用 **Sentinel-2 衛星影像** 結合 **隨機森林 (Random Forest)** 機器學習演算法。
        透過內置的深度資料資產進行 **20 公尺水深限制**，並套用 **形態學平滑處理** 以解決原始遮罩中的孔洞問題。
        """)

        with solara.Row(style={"gap": "20px"}):
            # 左側控制面板
            with solara.Column(style={"width": "350px"}):
                with solara.Card("控制面板"):
                    solara.Markdown("#### 1. 時間維度")
                    solara.Select(label="選擇監測年份", value=target_year, 
                                  values=[2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
                    
                    solara.Markdown("---")
                    solara.Markdown("#### 2. 影像優化 (解決孔洞問題)")
                    solara.SliderInt(label="遮罩平滑半徑 (公尺)", value=smoothing_radius, min=0, max=80)
                    solara.Info(f"目前的設定將會填補約 {smoothing_radius.value} 公尺範圍內的細小孔洞。")
                    
                    if smoothing_radius.value > 40:
                        solara.Warning("半徑過大可能會導致珊瑚礁邊緣過於模糊，建議設定在 20-40 之間。")

            # 右側地圖顯示
            with solara.Column(style={"flex": "1"}):
                with solara.Card(f"📍 {target_year.value} 年 棲地分布地圖"):
                    ReefClassificationMap(target_year.value, smoothing_radius.value)

            solara.Markdown("---")
            solara.Markdown("## 使用隨機森林做監督式分類")
            solara.Markdown("---")
