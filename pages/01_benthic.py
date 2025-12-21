import solara
import geemap.foliumap as geemap
import ee
import os
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# ==========================================
# 0. GEE 驗證與初始化 (終極容錯版)
# ==========================================
try:
    key_content = os.environ.get('EARTHENGINE_TOKEN')
    if key_content and key_content.strip():
        try:
            # 自動修正 JSON 格式 (單引號轉雙引號)
            clean_content = key_content.replace("'", '"')
            service_account_info = json.loads(clean_content)
            
            # 自動讀取 project_id
            my_project_id = service_account_info.get("project_id")
            
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(credentials=creds, project=my_project_id)
            print(f"✅ 雲端環境：GEE 驗證成功！(Project: {my_project_id})")
            init_status = "✅ GEE 連線成功"
        except Exception as e:
            print(f"⚠️ Token 解析失敗: {e}，嘗試使用本機驗證...")
            ee.Initialize()
            init_status = "⚠️ 本機驗證模式"
    else:
        print("⚠️ 無 Token，嘗試本機驗證...")
        ee.Initialize()
        init_status = "⚠️ 本機驗證模式"

except Exception as e:
    print(f"⚠️ GEE 初始化遭遇問題 ({e})")
    init_status = f"❌ 初始化異常: {e}"

# ==========================================
# 1. 數據準備 (Analysis Data)
# ==========================================
# 您提供的完整數據
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

# 定義顏色映射
color_map = {
    "沙地 (Sand)": "#ffffbe",
    "沙/藻 (Sand/Algae)": "#e0d05e",
    "硬珊瑚 (Hard Coral)": "#b19c3a", # 也可以改用綠色系 #2ecc71
    "軟珊瑚 (Soft Coral)": "#ff6161",
    "碎石 (Rubble)": "#9bcc4f",
    "海草 (Seagrass)": "#000000"
}

# ==========================================
# 2. 響應式變數
# ==========================================
target_year = solara.reactive(2024)
time_period = solara.reactive("夏季平均") 
selected_chart = solara.reactive("📈 折線趨勢")

# ROI 設定
ROI_RECT = ee.Geometry.Rectangle([119.2741, 23.1694, 119.8114, 23.8792])
ROI_CENTER = [23.5, 119.5]

# ==========================================
# 3. 組件定義：地圖邏輯 (含防呆)
# ==========================================
def save_map_to_html(m):
    try:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            temp_path = tmp.name
        m.to_html(filename=temp_path)
        with open(temp_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except Exception:
        return "<div>Map Error</div>"
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

@solara.component
def ReefHabitatMap(year, period):
    def get_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=11)
        m.add_basemap("HYBRID")
        m.addLayer(ROI_RECT, {'color': 'yellow', 'fillColor': '00000000'}, "ROI")

        # 設定時間
        if period == "夏季平均":
            start_date, end_date = f'{year}-06-01', f'{year}-09-30'
        else:
            start_date, end_date = f'{year}-01-01', f'{year}-12-31'

        try:
            # 1. 嘗試載入 Sentinel-2 影像
            s2_img = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterBounds(ROI_RECT)
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                      .median().clip(ROI_RECT))
            
            # 2. 顯示真實色彩影像 (底圖)
            vis_params = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}
            m.addLayer(s2_img, vis_params, f"{year} Sentinel-2 真實色彩")

            # 3. 嘗試載入分類 (如果您有上傳分類影像)
            # 這裡做一個簡單的 NDWI 水體遮罩當示範，避免程式掛掉
            ndwi = s2_img.normalizedDifference(['B3', 'B8'])
            water_mask = ndwi.gt(0)
            # m.addLayer(water_mask.selfMask(), {'palette': ['blue']}, "水體範圍")

        except Exception as e:
            print(f"地圖圖層載入錯誤: {e}")

        return save_map_to_html(m)

    map_html = solara.use_memo(get_map_html, dependencies=[year, period])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "600px", "style": "border: none;"})

# ==========================================
# 4. 組件定義：數據分析儀表板
# ==========================================
@solara.component
def AnalysisDashboard():
    
    # 建立折線圖
    def create_line_chart():
        df_melted = df_analysis.melt(id_vars=['Year'], var_name='Habitat', value_name='Area (ha)')
        fig = px.line(
            df_melted, x="Year", y="Area (ha)", color="Habitat", markers=True,
            title="澎湖珊瑚礁棲地歷年面積變化 (2016-2025)", color_discrete_map=color_map, height=450
        )
        fig.update_layout(xaxis=dict(tickmode='linear'), plot_bgcolor="white", hovermode="x unified")
        return fig

    # 建立堆疊長條圖
    def create_bar_chart():
        df_melted = df_analysis.melt(id_vars=['Year'], var_name='Habitat', value_name='Area (ha)')
        fig = px.bar(
            df_melted, x="Year", y="Area (ha)", color="Habitat",
            title="棲地組成比例堆疊圖", color_discrete_map=color_map, height=450
        )
        fig.update_layout(plot_bgcolor="white")
        return fig

    with solara.Card("📊 歷年數據分析報告", style={"margin-top": "20px"}):
        # 1. 切換按鈕
        solara.ToggleButtonsSingle(
            value=selected_chart, 
            values=["📈 折線趨勢", "📊 堆疊組成", "📋 原始數據"]
        )
        
        # 2. 顯示內容
        if selected_chart.value == "📈 折線趨勢":
            solara.FigurePlotly(create_line_chart())
            solara.Info("說明：可觀察硬珊瑚與軟珊瑚的消長趨勢。")
            
        elif selected_chart.value == "📊 堆疊組成":
            solara.FigurePlotly(create_bar_chart())
            
        elif selected_chart.value == "📋 原始數據":
            solara.DataFrame(df_analysis)

# ==========================================
# 5. 主頁面佈局
# ==========================================
@solara.component
def Page():
    # 使用 100% 寬度
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "100%", "margin": "0 auto"}):
        
        solara.Title("🪸 澎湖珊瑚礁棲地動態監測系統")
        solara.Markdown(f"**系統狀態**: {init_status}")
        
        # --- 第一部分：地圖與控制 ---
        with solara.Row(style={"gap": "20px", "flex-wrap": "wrap"}):
            # 左側控制與地圖
            with solara.Column(style={"flex": "1", "min-width": "500px"}):
                with solara.Card("🔍 監測工具箱 & 地圖"):
                    with solara.Row():
                        solara.SliderInt(label="年份", value=target_year, min=2016, max=2025)
                        solara.ToggleButtonsSingle(value=time_period, values=["夏季平均", "全年平均"])
                    
                    ReefHabitatMap(target_year.value, time_period.value)
                    solara.Info("地圖顯示：Sentinel-2 衛星合成影像 (ROI 範圍)")

            # --- 第二部分：數據分析 ---
            with solara.Column(style={"flex": "1", "min-width": "500px"}):
                AnalysisDashboard()
        
        solara.Markdown("---")
        solara.Markdown("""
        ### 🪸 硬珊瑚與軟珊瑚簡介
        - **硬珊瑚 (Hard Coral)**：又稱造礁珊瑚，擁有堅固的鈣質外骨骼，是珊瑚礁的基石。
        - **軟珊瑚 (Soft Coral)**：無鈣質外骨骼，對環境變化反應不同於硬珊瑚。
        """)