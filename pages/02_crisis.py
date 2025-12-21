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
# 1. 全域設定與資料準備
# ==========================================
ROI_RECT = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])
ROI_CENTER = [23.5, 119.5]

# Reactive 變數
sst_year = solara.reactive(2024)
sst_type = solara.reactive("夏季均溫")
ndci_year = solara.reactive(2025)

# 數據整合
years_list = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
sst_values = [28.16, 27.75, 28.62, 28.37, 28.29, 28.02, 28.95, 28.43]
hard_coral_values = [1584.55, 382.45, 76.97, 197.21, 95.55, 224.21, 239.71, 1264.49]
soft_coral_values = [27021.95, 39909.45, 13074.83, 22751.8, 15645.15, 25062.1, 42609.19, 26497.41]
total_coral_values = [28606.5, 40291.9, 13151.8, 22949.0, 15740.7, 25286.3, 42849.9, 27761.9]
ndci_mean_values = [-0.063422, 0.041270, 0.041549, 0.041954, 0.093461, 0.107500, 0.108534, 0.066040]

df_mixed = pd.DataFrame({'Year': years_list, 'SST_Summer': sst_values, 'Hard_Coral': hard_coral_values, 'Soft_Coral': soft_coral_values})
df_ndci = pd.DataFrame({'Year': years_list, 'NDCI_Mean': ndci_mean_values})

# ==========================================
# 2. 共用函式
# ==========================================
def save_map_to_html(m):
    try:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            temp_path = tmp.name
        m.to_html(filename=temp_path)
        with open(temp_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except Exception as e:
        return f"<div style='color:red'>地圖生成錯誤: {str(e)}</div>"
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

# ==========================================
# 3. 組件：圖表與地圖
# ==========================================

@solara.component
def SSTMap(year, period_type):
    def get_sst_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=10)
        start_date, end_date = (f'{year}-06-01', f'{year}-09-30') if period_type == "夏季均溫" else (f'{year}-01-01', f'{year}-12-31')
        try:
            if year < 2018:
                dataset = ee.ImageCollection("NASA/OCEANDATA/MODIS-Aqua/L3SMI").filterBounds(ROI_RECT).filterDate(start_date, end_date).select('sst').median().clip(ROI_RECT)
                source = "NASA MODIS"
            else:
                dataset = ee.ImageCollection('JAXA/GCOM-C/L3/OCEAN/SST/V3').filterBounds(ROI_RECT).filterDate(start_date, end_date).filter(ee.Filter.eq('SATELLITE_DIRECTION', 'D')).median().clip(ROI_RECT).select('SST_AVE').multiply(0.0012).add(-10)
                source = "JAXA GCOM-C"
            sst_vis = {"min": 25, "max": 33, "palette": ['000000', '005aff', '43c8c8', 'fff700', 'ff0000']}
            m.addLayer(dataset, sst_vis, f"{year} SST ({source})")
            m.add_colorbar(sst_vis, label="海面溫度 (°C)")
        except: pass
        return save_map_to_html(m)
    map_html = solara.use_memo(get_sst_map_html, dependencies=[year, period_type])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def SSTCoralChart():
    with solara.Card("📊 關聯分析：海溫 vs 硬/軟珊瑚面積"):
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_mixed['Year'], y=df_mixed['Hard_Coral'], name='硬珊瑚 (m²)', marker_color='rgba(46, 204, 113, 0.7)', yaxis='y2'))
        fig.add_trace(go.Bar(x=df_mixed['Year'], y=df_mixed['Soft_Coral'], name='軟珊瑚 (m²)', marker_color='rgba(241, 196, 15, 0.5)', yaxis='y3'))
        fig.add_trace(go.Scatter(x=df_mixed['Year'], y=df_mixed['SST_Summer'], name='夏季均溫 (°C)', mode='lines+markers', line=dict(color='#e74c3c', width=4)))
        fig.update_layout(
            xaxis=dict(title='年份', tickmode='linear'),
            yaxis=dict(title='海溫 (°C)', font=dict(color="#e74c3c"), range=[27, 30], side='left'),
            yaxis2=dict(title='硬珊瑚 (m²)', font=dict(color="#27ae60"), overlaying='y', side='right', range=[0, 2000]),
            yaxis3=dict(title='軟珊瑚 (m²)', font=dict(color="#f39c12"), overlaying='y', side='right', position=1, anchor='free', range=[0, 45000]),
            legend=dict(x=0.5, y=-0.2, xanchor='center', orientation="h"),
            margin=dict(l=50, r=100, t=60, b=100), height=500
        )
        solara.FigurePlotly(fig)

@solara.component
def NDCIMap(year):
    def get_ndci_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=11)
        start_date, end_date = f'{year}-05-01', f'{year}-09-30'
        col = 'COPERNICUS/S2_SR_HARMONIZED' if year >= 2019 else 'COPERNICUS/S2_HARMONIZED'
        s2 = ee.ImageCollection(col).filterDate(start_date, end_date).filterBounds(ROI_RECT).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        img_ndci = s2.median().clip(ROI_RECT).normalizedDifference(['B5', 'B4'])
        vis = {'min': -0.05, 'max': 0.15, 'palette': ['#0011ff', '#00ff00', '#ff0000']}
        m.addLayer(img_ndci, vis, 'NDCI')
        m.add_colorbar(vis, label="NDCI (優養化)")
        return save_map_to_html(m)
    map_html = solara.use_memo(get_ndci_map_html, dependencies=[year])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def NDCIChart():
    with solara.Card("📊 關聯分析：NDCI vs 硬/軟珊瑚面積"):
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_ndci['Year'], y=hard_coral_values, name='硬珊瑚 (m²)', marker_color='rgba(46, 204, 113, 0.7)', yaxis='y2'))
        fig.add_trace(go.Bar(x=df_ndci['Year'], y=soft_coral_values, name='軟珊瑚 (m²)', marker_color='rgba(241, 196, 15, 0.5)', yaxis='y3'))
        fig.add_trace(go.Scatter(x=df_ndci['Year'], y=df_ndci['NDCI_Mean'], name='NDCI', mode='lines+markers', line=dict(color='#00CC96', width=3)))
        fig.update_layout(
            xaxis=dict(title='年份', tickmode='linear'),
            yaxis=dict(title='NDCI 指數', font=dict(color="#00CC96"), side='left'),
            yaxis2=dict(title='硬珊瑚 (m²)', overlaying='y', side='right', range=[0, 2000]),
            yaxis3=dict(title='軟珊瑚 (m²)', overlaying='y', side='right', position=1, anchor='free', range=[0, 45000]),
            legend=dict(x=0.5, y=-0.2, xanchor='center', orientation="h"),
            margin=dict(l=50, r=100, t=50, b=100), height=500
        )
        solara.FigurePlotly(fig)

@solara.component
def StarfishMap():
    def get_starfish_map_html():
        m = geemap.Map(center=[23.25, 119.55], zoom=11)
        m.add_basemap("HYBRID")
        zones = [ee.Feature(ee.Geometry.Rectangle([119.408, 23.185, 119.445, 23.215]), {'name': '七美嶼'})] # 範例僅列一處
        m.addLayer(ee.FeatureCollection(zones).style(color='red', width=3, fillColor='00000000'), {}, "警戒區")
        return save_map_to_html(m)
    return solara.HTML(tag="iframe", attributes={"srcDoc": solara.use_memo(get_starfish_map_html, []), "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def CorrelationAnalysis():
    with solara.Card("🧮 統計分析：皮爾森相關係數"):
        df_corr = pd.DataFrame({'SST': sst_values, 'NDCI': ndci_mean_values, 'Hard': hard_coral_values, 'Soft': soft_coral_values})
        corr = df_corr.corr().round(2)
        fig = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale='RdBu_r', zmin=-1, zmax=1, text=corr.values, texttemplate="%{text}"))
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
        solara.FigurePlotly(fig)

# ==========================================
# 4. 主頁面佈局
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "1200px", "margin": "0 auto"}):
        solara.Markdown("# 🌊 危害澎湖珊瑚礁之各項因子監測平台")
        
        with solara.Card("1. 海溫異常 (SST)"):
            with solara.Row(gap="20px"):
                with solara.Column(style={"flex": "1"}):
                    solara.SliderInt("年份", value=sst_year, min=2018, max=2025)
                    solara.ToggleButtonsSingle(value=sst_type, values=["全年平均", "夏季均溫"])
                    SSTMap(sst_year.value, sst_type.value)
                with solara.Column(style={"flex": "1"}):
                    SSTCoralChart()

        with solara.Card("2. 海洋優養化 (NDCI)"):
            with solara.Row(gap="20px"):
                with solara.Column(style={"flex": "1"}):
                    solara.SliderInt("年份", value=ndci_year, min=2018, max=2025)
                    NDCIMap(ndci_year.value)
                with solara.Column(style={"flex": "1"}):
                    NDCIChart()

        with solara.Card("3. 棘冠海星警戒"):
            with solara.Row(gap="20px"):
                with solara.Column(style={"flex": "2"}): StarfishMap()
                with solara.Column(style={"flex": "1"}):
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%")
                    solara.Markdown("**棘冠海星**: 七美及南方四島現況已有爆發跡象。")

        with solara.Card("4. 皮爾森相關性分析"):
            CorrelationAnalysis()

        with solara.Card("5. 人類活動影響"):
            solara.Markdown("### 🗺️ 海廢熱點與廢棄漁網分佈圖 (iOcean)")
            solara.HTML(tag="iframe", attributes={
                "src": "https://iocean.oca.gov.tw/iOceanMap/map.aspx",
                "width": "100%", "height": "600px",
                "style": "border: 1px solid #ddd; border-radius: 12px;",
                "loading": "lazy"
            })
            solara.Markdown("> **資料來源：** [海洋委員會海洋保育署 - 海洋保育網 (iOcean)](https://iocean.oca.gov.tw/iOceanMap/map.aspx)")

        solara.Markdown("---")
        solara.Markdown("資料來源：NASA, JAXA, ESA, 海洋保育署 | Update: 2025.12")