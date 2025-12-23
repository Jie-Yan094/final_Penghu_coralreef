import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# ==========================================
# 0. GEE 驗證與初始化
# ==========================================
ee_initialized = False
try:
    key_content = os.environ.get('EARTHENGINE_TOKEN')
    if key_content and key_content.strip():
        try:
            clean_content = key_content.replace("'", '"')
            service_account_info = json.loads(clean_content)
            my_project_id = service_account_info.get("project_id")
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(credentials=creds, project=my_project_id)
            print(f"✅ 雲端環境：GEE 驗證成功！(Project: {my_project_id})")
            ee_initialized = True
        except Exception as e:
            print(f"⚠️ Token 驗證失敗: {e}")
            try:
                ee.Initialize()
                ee_initialized = True
            except:
                pass
    else:
        try:
            ee.Initialize()
            ee_initialized = True
        except:
            pass
except Exception as e:
    print(f"⚠️ GEE 初始化遭遇問題 ({e})")

# ==========================================
# 1. 資料準備 (已正名)
# ==========================================
ROI_RECT = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])
ROI_CENTER = [23.5, 119.5]

# 數據標籤已更新為 ACA 官方定義
raw_data = {
    "Year": [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "沙地 (Sand)": [927.48, 253.14, 4343.63, 1471.55, 541.53, 919.71, 322.23, 677.92, 260.38, 5485.41],
    "微藻墊 (Microalgal Mats)": [1520.33, 81.28, 4533.96, 1507.81, 134.95, 334.42, 209.84, 322.38, 280.27, 1794.93],
    "珊瑚/藻類 (Coral/Algae)": [342.08, 92.92, 1584.55, 382.45, 76.97, 197.21, 95.55, 224.21, 239.71, 1264.49],
    "岩石 (Rock)": [32272.96, 10536.69, 27021.90, 39909.48, 13074.81, 22751.79, 15645.10, 25062.07, 42610.23, 26497.39],
    "碎石 (Rubble)": [3604.92, 300.24, 6416.81, 7185.07, 741.91, 793.30, 1043.67, 2006.07, 2367.72, 9170.30],
    "海草 (Seagrass)": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}
df_analysis = pd.DataFrame(raw_data)

# 顏色設定 (同步 ACA 風格)
color_map = {
    "沙地 (Sand)": "#ffffbe",
    "微藻墊 (Microalgal Mats)": "#9bcc4f",
    "珊瑚/藻類 (Coral/Algae)": "#00ced1", # 亮藍綠
    "岩石 (Rock)": "#8B4513",            # 深褐
    "碎石 (Rubble)": "#808080",          # 灰
    "海草 (Seagrass)": "#668438"         # 深綠
}

target_year = solara.reactive(2024)
time_period = solara.reactive("夏季平均")
smoothing_radius = solara.reactive(30)
selected_chart = solara.reactive("📈 折線趨勢")

# ==========================================
# 2. 地圖組件
# ==========================================
def save_map_to_html(m):
    try:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            temp_path = tmp.name
        m.to_html(filename=temp_path)
        with open(temp_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return html_content
    except Exception as e:
        return f"<div style='color:red; border:1px solid red; padding:10px;'>Map Error: {str(e)}</div>"

@solara.component
def ReefHabitatMap(year, period, radius):
    def get_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=11)
        m.add_basemap("HYBRID")

        if not ee_initialized:
            return save_map_to_html(m)

        try:
            # 1. 時間與資料源設定
            if period == "夏季平均":
                start_date, end_date = f'{year}-06-01', f'{year}-09-30'
            else:
                start_date, end_date = f'{year}-01-01', f'{year}-12-31'

            if year >= 2019:
                s2_collection_id = "COPERNICUS/S2_SR_HARMONIZED"
                dataset_label = "Sentinel-2 SR (大氣校正)"
            else:
                s2_collection_id = "COPERNICUS/S2_HARMONIZED"
                dataset_label = "Sentinel-2 TOA (頂層大氣)"

            # 2. 水深遮罩
            try:
                depth_raw = ee.Image('projects/ee-s1243041/assets/bathymetry_0')
                actual_band = depth_raw.bandNames().get(0)
                depth_img = depth_raw.select([actual_band]).rename('depth').clip(ROI_RECT)
                depth_mask = depth_img.lt(30).And(depth_img.gt(0))
            except:
                depth_mask = ee.Image(1).clip(ROI_RECT)

            # 3. 準備訓練資料
            def smooth(mask, r):
                return mask.focal_mode(radius=r, kernelType='circle', units='meters')

            img_train = (ee.ImageCollection(s2_collection_id)
                         .filterBounds(ROI_RECT).filterDate('2018-01-01', '2018-12-31')
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                         .median().clip(ROI_RECT).select(['B2','B3','B4','B8']))

            mask_train = smooth(img_train.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), 10)
            
            # [關鍵修正] ACA Remap 對應表
            # 11:沙, 18:微藻墊, 15:珊瑚/藻類, 13:岩石, 12:碎石, 14:海草
            label_img = ee.Image('ACA/reef_habitat/v2_0').clip(ROI_RECT).remap(
                [0, 11, 18, 15, 13, 12, 14], 
                [0,  1,  2,  3,  4,  5,  6], 
                0
            ).rename('benthic').toByte()

            sample = img_train.updateMask(mask_train).addBands(label_img).stratifiedSample(
                numPoints=1000, 
                classBand='benthic', 
                region=ROI_RECT, 
                scale=30,
                tileScale=8, 
                geometries=False
            )
            
            classifier = ee.Classifier.smileRandomForest(50).train(sample, 'benthic', img_train.bandNames())

            # 4. 目標年份分類
            target_img = (ee.ImageCollection(s2_collection_id)
                          .filterBounds(ROI_RECT).filterDate(start_date, end_date)
                          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                          .median().clip(ROI_RECT).select(['B2','B3','B4','B8']))

            target_ndwi_mask = target_img.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask)

            classified_raw = target_img.updateMask(target_ndwi_mask).classify(classifier)

            if radius > 0:
                classified = classified_raw.focal_mode(radius=radius, kernelType='circle', units='meters')
            else:
                classified = classified_raw

            # 5. 視覺化 (正名配色)
            # 0:黑, 1:沙, 2:微藻墊, 3:珊瑚/藻類, 4:岩石, 5:碎石, 6:海草
            new_palette = [
                '000000', # 0
                '#ffffbe', # 1 Sand
                '#9bcc4f', # 2 Mats
                '#00ced1', # 3 Coral/Algae
                '#8B4513', # 4 Rock
                '#808080', # 5 Rubble
                '#668438'  # 6 Seagrass
            ]
            class_vis = {'min': 0, 'max': 6, 'palette': new_palette}
            
            m.addLayer(target_img, {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}, f"{year} 衛星影像 ({dataset_label})")
            m.addLayer(classified, class_vis, f"{year} AI分類結果")
            m.add_legend(title="棲地類別", labels=["無數據", "沙地", "微藻墊", "珊瑚/藻類", "岩石", "碎石", "海草"], colors=new_palette)

        except Exception as e:
            return f"<div style='color:red'>分類運算錯誤: {str(e)}<br>建議：請切換至其他年份試試。</div>"

        return save_map_to_html(m)

    map_html = solara.use_memo(get_map_html, dependencies=[year, period, radius])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "750px", "style": "border: none;"})

# ==========================================
# 3. 數據分析儀表板
# ==========================================
@solara.component
def AnalysisDashboard():
    def create_line_chart():
        df_melted = df_analysis.melt(id_vars=['Year'], var_name='Habitat', value_name='Area (ha)')
        fig = px.line(
            df_melted, x="Year", y="Area (ha)", color="Habitat", markers=True,
            title="澎湖珊瑚礁棲地歷年面積變化 (2016-2025)", color_discrete_map=color_map, height=450
        )
        fig.update_layout(xaxis=dict(tickmode='linear'), plot_bgcolor="white", hovermode="x unified")
        return fig

    def create_bar_chart():
        df_melted = df_analysis.melt(id_vars=['Year'], var_name='Habitat', value_name='Area (ha)')
        fig = px.bar(
            df_melted, x="Year", y="Area (ha)", color="Habitat",
            title="棲地組成比例堆疊圖", color_discrete_map=color_map, height=450
        )
        fig.update_layout(plot_bgcolor="white")
        return fig

    with solara.Card("📊 歷年數據分析報告", style={"margin-top": "20px"}):
        solara.ToggleButtonsSingle(value=selected_chart, values=["📈 折線趨勢", "📊 堆疊組成", "📋 原始數據"])
        
        if selected_chart.value == "📈 折線趨勢":
            solara.FigurePlotly(create_line_chart())
        elif selected_chart.value == "📊 堆疊組成":
            solara.FigurePlotly(create_bar_chart())
        elif selected_chart.value == "📋 原始數據":
            solara.DataFrame(df_analysis)

# ==========================================
# 4. 主頁面
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "100%", "margin": "0 auto"}):
        solara.Title("🪸 澎湖珊瑚礁棲地動態監測系統")
        
        status_text = "GEE 連線正常" if ee_initialized else "GEE 連線失敗"
        status_color = "green" if ee_initialized else "red"
        solara.Markdown(f"**系統狀態**: <span style='color:{status_color}'>{status_text}</span>")

        with solara.Row(style={"gap": "20px", "flex-wrap": "wrap"}):
            with solara.Column(style={"width": "350px", "min-width": "300px"}):
                with solara.Card("🔍 監測工具箱"):
                    solara.Markdown("#### 1. 時間範圍")
                    solara.SliderInt(label="年份", value=target_year, min=2016, max=2025)
                    solara.ToggleButtonsSingle(value=time_period, values=["夏季平均", "全年平均"])
                    
                    solara.Markdown("#### 2. 影像優化")
                    solara.SliderInt(label="平滑半徑 (m)", value=smoothing_radius, min=0, max=80)
                
                with solara.Card("💡 說明"):
                    solara.Markdown("系統使用 Sentinel-2 衛星影像結合隨機森林 (Random Forest) 演算法進行即時棲地分類。")

            with solara.Column(style={"flex": "1", "min-width": "500px"}):
                with solara.Card(f"📍 {target_year.value} 年棲地分布"):
                    ReefHabitatMap(target_year.value, time_period.value, smoothing_radius.value)

        solara.Markdown("---")
        AnalysisDashboard()