import solara
import geemap.foliumap as geemap
import ee
import os
import json
import time
from google.oauth2.service_account import Credentials

# ==========================================
# 0. GEE 驗證與初始化
# ==========================================
def initialize_ee():
    try:
        token = os.environ.get('MEOWEARTHENGINE_TOKEN')
        if token:
            try:
                info = json.loads(token)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/earthengine'])
                ee.Initialize(credentials=creds, project='ee-s1243041')
                return "✅ 雲端認證成功"
            except Exception as json_err:
                return f"❌ JSON 格式錯誤: {json_err}"
        else:
            ee.Initialize(project='ee-s1243041')
            return "⚠️ 本機環境認證"
    except Exception as e:
        return f"❌ 初始化失敗: {e}"

init_status = initialize_ee()

# ==========================================
# 1. 響應式變數定義
# ==========================================
target_year = solara.reactive(2024)
time_period = solara.reactive("夏季平均") 
smoothing_radius = solara.reactive(30)   

# ==========================================
# 2. 地圖組件
# ==========================================
@solara.component
def ReefHabitatMap(year, period, radius):
    def get_map_html():
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        roi = ee.Geometry.Rectangle([119.2741, 23.1694, 119.8114, 23.8792])
        
        # A. 設定日期區間
        if period == "夏季平均":
            start_date, end_date = f'{year}-06-01', f'{year}-09-30'
        else:
            start_date, end_date = f'{year}-01-01', f'{year}-12-31'

        # B. 深度資料與遮罩
        depth_raw = ee.Image('projects/ee-s1243041/assets/bathymetry_0')
        actual_band = depth_raw.bandNames().get(0)
        depth_img = depth_raw.select([actual_band]).rename('depth').clip(roi)
        depth_mask = depth_img.lt(2000).And(depth_img.gt(0))

        # C. 形態學平滑工具 (Helper)
        def smooth(mask, r):
            return mask.focal_mode(radius=r, units='meters', kernelType='circle')

        # ==========================================
        # D. 訓練模型 (參數固定化，避免重複訓練)
        # ==========================================
        img_train = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                     .filterBounds(roi).filterDate('2018-01-01', '2018-12-31')
                     .median().clip(roi).select('B.*'))
        
        # 固定訓練集遮罩半徑 (10m)
        mask_train = smooth(img_train.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), 10)

        # 修正 remap 參數
        label_img = ee.Image('ACA/reef_habitat/v2_0').clip(roi).remap(
            [0, 11, 12, 13, 14, 15, 18], 
            [0, 1, 2, 3, 4, 5, 6], 
            0
        ).rename('benthic').toByte()
        
        # 訓練採樣設定
        sample = img_train.updateMask(mask_train).addBands(label_img).stratifiedSample(
            numPoints=1000, 
            classBand='benthic', 
            region=roi, 
            scale=30,      
            tileScale=4,   
            geometries=False
        )

        classifier = ee.Classifier.smileRandomForest(50).train(
            sample, 'benthic', img_train.bandNames()
        )

        # ==========================================
        # E. 處理目標年份影像
        # ==========================================
        target_img = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                      .filterBounds(roi).filterDate(start_date, end_date)
                      .median().clip(roi).select('B.*'))
        
        target_ndwi_mask = target_img.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask)
        
        # 應用動態平滑邏輯
        if radius > 0:
            mask_target = smooth(target_ndwi_mask, radius)
            water_target = target_img.updateMask(mask_target)
            classified_raw = water_target.classify(classifier)
            classified = smooth(classified_raw, radius)
        else:
            mask_target = target_ndwi_mask
            water_target = target_img.updateMask(mask_target)
            classified = water_target.classify(classifier)

        # F. 可視化
        s2_vis = {'min': 100, 'max': 3500, 'bands': ['B4', 'B3', 'B2']}
        class_vis = {'min': 0, 'max': 6, 'palette': ['000000', 'ffffbe', 'e0d05e', 'b19c3a', '668438', 'ff6161', '9bcc4f']}
        
        m.addLayer(water_target, s2_vis, f"{year} {period} 底圖")
        m.addLayer(classified, class_vis, f"{year} 棲地分類結果")
        
        m.add_legend(title="棲地類別", labels=["無數據", "沙地", "沙/藻", "硬珊瑚", "軟珊瑚", "碎石", "海草"], colors=class_vis['palette'])
        
        # ★★★ 修正處：將 outfile 改為 filename ★★★
        output_path = f"/tmp/map_{int(time.time())}.html"
        return m.to_html(filename=output_path)

    map_html = solara.use_memo(get_map_html, dependencies=[year, period, radius])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "750px", "style": "border: none;"})

# ==========================================
# 3. 介面佈局
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"padding": "30px", "background-color": "#f4f7f9"}):
        solara.Title("澎湖珊瑚礁棲地動態監測系統")
        solara.Markdown(f"**系統狀態**: {init_status}")

        with solara.Row(style={"gap": "20px"}):
            # 左側控制面板
            with solara.Column(style={"width": "380px"}):
                with solara.Card("🔍 監測工具箱"):
                    solara.Markdown("#### 1. 時間範圍選擇")
                    solara.SliderInt(label="選擇監測年份", value=target_year, min=2016, max=2025)
                    
                    solara.Markdown("#### 2. 統計區間")
                    solara.ToggleButtonsSingle(value=time_period, values=["夏季平均", "全年平均"])
                    
                    solara.Markdown("---")
                    solara.Markdown("#### 3. 影像優化 (填補孔洞)")
                    solara.SliderInt(label="平滑半徑 (m)", value=smoothing_radius, min=0, max=80)
                    solara.Info(f"目前的設定會根據 {time_period.value} 影像填補約 {smoothing_radius.value} 公尺內的孔洞。")

                with solara.Card("💡 說明"):
                    solara.Markdown(f"""
                    - **夏季平均**：聚焦 6-9 月影像，可觀察極端氣候對珊瑚礁的即時光譜影響。
                    - **全年平均**：利用整年數據中值，消除單一季節的雲霧干擾，獲得最穩定的底質分類。
                    """)

            # 右側地圖顯示
            with solara.Column(style={"flex": "1"}):
                with solara.Card(f"📍 {target_year.value} 年 {time_period.value} - 棲地分布地圖"):
                    ReefHabitatMap(target_year.value, time_period.value, smoothing_radius.value)

# 啟動 Page
Page()