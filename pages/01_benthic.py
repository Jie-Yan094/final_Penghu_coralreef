import solara
import geemap.foliumap as geemap
import ee
import os
import json
import time
import pandas as pd
import plotly.express as px
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
# 1. 數據準備 (Analysis Data)
# ==========================================
raw_data = {
    "Year": [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "沙地 (Sand)": [927.48, 253.14, 4343.63, 1471.55, 541.53, 919.71, 322.23, 677.92, 260.38, 5485.41],
    "沙/藻 (Sand/Algae)": [1520.33, 81.28, 4533.96, 1507.81, 134.95, 334.42, 209.84, 322.38, 280.27, 1794.93],
    "硬珊瑚 (Hard Coral)": [342.08, 92.92, 1584.55, 382.45, 76.97, 197.21, 95.55, 224.21, 239.71, 1264.49],
    "軟珊瑚 (Soft Coral)": [32272.96, 10536.69, 27021.90, 39909.48, 13074.81, 22751.79, 15645.10, 25062.07, 42610.23, 26497.39],
    "碎石 (Rubble)": [3604.92, 300.24, 6416.81, 7185.07, 741.91, 793.30, 1043.67, 2006.07, 2367.72, 9170.30],
    "海草 (Seagrass)": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}
df_analysis = pd.DataFrame(raw_data)

color_map = {
    "沙地 (Sand)": "#ffffbe",
    "沙/藻 (Sand/Algae)": "#e0d05e",
    "硬珊瑚 (Hard Coral)": "#b19c3a",
    "軟珊瑚 (Soft Coral)": "#ff6161",
    "碎石 (Rubble)": "#9bcc4f",
    "海草 (Seagrass)": "#000000"
}

# ==========================================
# 2. 響應式變數定義
# ==========================================
target_year = solara.reactive(2024)
time_period = solara.reactive("夏季平均") 
smoothing_radius = solara.reactive(30)
# 新增：控制圖表切換的變數
selected_chart = solara.reactive("📈 折線趨勢")

# ==========================================
# 3. 組件定義：地圖邏輯
# ==========================================
@solara.component
def ReefHabitatMap(year, period, radius):
    def get_map_html():
        m = geemap.Map(center=[23.5, 119.5], zoom=11)
        roi = ee.Geometry.Rectangle([119.2741, 23.1694, 119.8114, 23.8792])
        
        if period == "夏季平均":
            start_date, end_date = f'{year}-06-01', f'{year}-09-30'
        else:
            start_date, end_date = f'{year}-01-01', f'{year}-12-31'

        depth_raw = ee.Image('projects/ee-s1243041/assets/bathymetry_0')
        actual_band = depth_raw.bandNames().get(0)
        depth_img = depth_raw.select([actual_band]).rename('depth').clip(roi)
        depth_mask = depth_img.lt(2000).And(depth_img.gt(0))

        def smooth(mask, r):
            return mask.focal_mode(radius=r, units='meters', kernelType='circle')

        img_train = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                     .filterBounds(roi).filterDate('2018-01-01', '2018-12-31')
                     .median().clip(roi).select('B.*'))
        
        mask_train = smooth(img_train.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask), 10)

        label_img = ee.Image('ACA/reef_habitat/v2_0').clip(roi).remap(
            [0, 11, 12, 13, 14, 15, 18], [0, 1, 2, 3, 4, 5, 6], 0
        ).rename('benthic').toByte()
        
        sample = img_train.updateMask(mask_train).addBands(label_img).stratifiedSample(
            numPoints=1000, classBand='benthic', region=roi, scale=30, tileScale=4, geometries=False
        )

        classifier = ee.Classifier.smileRandomForest(50).train(sample, 'benthic', img_train.bandNames())

        target_img = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                      .filterBounds(roi).filterDate(start_date, end_date)
                      .median().clip(roi).select('B.*'))
        
        target_ndwi_mask = target_img.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask)
        
        if radius > 0:
            mask_target = smooth(target_ndwi_mask, radius)
            water_target = target_img.updateMask(mask_target)
            classified = smooth(water_target.classify(classifier), radius)
        else:
            mask_target = target_ndwi_mask
            water_target = target_img.updateMask(mask_target)
            classified = water_target.classify(classifier)

        s2_vis = {'min': 100, 'max': 3500, 'bands': ['B4', 'B3', 'B2']}
        class_vis = {'min': 0, 'max': 6, 'palette': ['000000', 'ffffbe', 'e0d05e', 'b19c3a', '668438', 'ff6161', '9bcc4f']}
        
        m.addLayer(water_target, s2_vis, f"{year} {period} 底圖")
        m.addLayer(classified, class_vis, f"{year} 棲地分類結果")
        m.add_legend(title="棲地類別", labels=["無數據", "沙地", "沙/藻", "硬珊瑚", "軟珊瑚", "碎石", "海草"], colors=class_vis['palette'])
        
        output_path = f"/tmp/map_{int(time.time())}.html"
        return m.to_html(filename=output_path)

    map_html = solara.use_memo(get_map_html, dependencies=[year, period, radius])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "750px", "style": "border: none;"})

# ==========================================
# 4. 組件定義：數據分析 (手動分頁版)
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
        # 1. 切換按鈕 (替代 Tabs，這一定會動)
        solara.ToggleButtonsSingle(
            value=selected_chart, 
            values=["📈 折線趨勢", "📊 堆疊組成", "📋 原始數據"]
        )
        solara.Markdown("---")
        
        # 2. 根據按鈕值顯示對應內容
        if selected_chart.value == "📈 折線趨勢":
            solara.FigurePlotly(create_line_chart())
            solara.Info("說明：軟珊瑚為主要優勢物種，面積波動與氣候事件高度相關。")
            
        elif selected_chart.value == "📊 堆疊組成":
            solara.FigurePlotly(create_bar_chart())
            
        elif selected_chart.value == "📋 原始數據":
            solara.DataFrame(df_analysis)

# ==========================================
# 5. 主頁面佈局
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"padding": "30px", "background-color": "#f4f7f9"}):
        solara.Title("澎湖珊瑚礁棲地動態監測系統")
        solara.Markdown(f"**系統狀態**: {init_status}")

        # --- 第一部分：互動地圖 ---
        with solara.Row(style={"gap": "20px"}):
            with solara.Column(style={"width": "350px"}):
                with solara.Card("🔍 監測工具箱"):
                    solara.Markdown("#### 1. 時間範圍")
                    solara.SliderInt(label="年份", value=target_year, min=2016, max=2025)
                    solara.ToggleButtonsSingle(value=time_period, values=["夏季平均", "全年平均"])
                    
                    solara.Markdown("#### 2. 影像優化")
                    solara.SliderInt(label="平滑半徑 (m)", value=smoothing_radius, min=0, max=80)
                    
                with solara.Card("💡 說明"):
                    solara.Markdown("夏季平均聚焦 6-9 月影像；全年平均使用整年數據中值。")

            with solara.Column(style={"flex": "1"}):
                with solara.Card(f"📍 {target_year.value} 年棲地分布"):
                    ReefHabitatMap(target_year.value, time_period.value, smoothing_radius.value)

        solara.Markdown("---")

        # --- 第二部分：數據分析 ---
        AnalysisDashboard()

# 啟動 Page
Page()