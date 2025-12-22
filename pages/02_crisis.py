import solara
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
import pandas as pd
import numpy as np
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
            print(f"⚠️ Token 解析失敗: {e}，嘗試使用本機驗證...")
            try:
                ee.Initialize()
                ee_initialized = True
            except:
                pass
    else:
        print("⚠️ 無 Token，嘗試本機驗證...")
        try:
            ee.Initialize()
            ee_initialized = True
        except:
            pass
except Exception as e:
    print(f"⚠️ GEE 初始化遭遇問題 ({e})")

# ==========================================
# 1. 全域設定與資料準備
# ==========================================
ROI_RECT = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])
ROI_CENTER = [23.5, 119.5]

# Reactive 變數
sst_year = solara.reactive(2024)
sst_type = solara.reactive("夏季均溫")
ndci_year = solara.reactive(2025)
coral_display_type = solara.reactive("硬珊瑚") 
selected_island = solara.reactive("七美嶼")

# --- 全區總表 (環境因子) ---
years_list = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
sst_values = [28.16, 27.75, 28.62, 28.37, 28.29, 28.02, 28.95, 28.43]
# 這裡保留原始的全區統計供參考
total_coral_values = [28606.5, 40291.9, 13151.8, 22949.0, 15740.7, 25286.3, 42849.9, 27761.9]
hard_coral_values = [1584.55, 382.45, 76.97, 197.21, 95.55, 224.21, 239.71, 1264.49]
soft_coral_values = [t - h for t, h in zip(total_coral_values, hard_coral_values)]

df_mixed = pd.DataFrame({
    'Year': years_list, 'SST_Summer': sst_values,
    'Hard_Coral': hard_coral_values, 'Soft_Coral': soft_coral_values, 'Total_Coral': total_coral_values
})
ndci_data = {'Year': years_list, 'NDCI_Mean': [-0.063422, 0.041270, 0.041549, 0.041954, 0.093461, 0.107500, 0.108534, 0.066040]}
df_ndci = pd.DataFrame(ndci_data)

# ==============================================================================
# 📊 真實數據注入區 (來自 Colab 運算結果)
# ==============================================================================
island_data = {
    '七美嶼': pd.DataFrame({
        'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'Hard_Coral': [26705.88, 24152.08, 39278.9, 16399.05, 12258.98, 12282.06, 11824.55, 17199.29, 15003.7, 14271.65],
        'Soft_Coral': [7681262.01, 5283528.45, 6360294.37, 5308001.78, 5304523.99, 5310355.43, 5253886.85, 5212946.0, 5301573.67, 5241927.13]
    }),
    '東吉嶼': pd.DataFrame({
        'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'Hard_Coral': [25400.08, 823.07, 1737.59, 3718.63, 1280.33, 731.61, 1188.87, 1005.98, 1097.42, 1097.42],
        'Soft_Coral': [2479597.09, 1478704.85, 1468082.05, 1718248.92, 1453507.28, 1441414.47, 1438919.24, 1452095.78, 1454809.77, 1451006.01]
    }),
    '西吉嶼': pd.DataFrame({
        'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'Hard_Coral': [14747.11, 1463.31, 2012.05, 457.28, 1463.3, 1188.94, 914.57, 457.28, 365.83, 640.19],
        'Soft_Coral': [1521217.54, 795385.68, 786914.56, 791830.19, 792664.34, 783850.72, 788697.92, 781027.09, 783828.01, 789075.23]
    }),
    '東嶼坪': pd.DataFrame({
        'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'Hard_Coral': [8321.42, 1737.54, 2834.94, 1188.84, 1371.73, 1005.94, 1920.44, 2194.79, 914.5, 1097.4],
        'Soft_Coral': [1002711.46, 448699.35, 444513.94, 451788.52, 453160.5, 448813.1, 448404.18, 442412.78, 451399.71, 457663.31]
    }),
    '西嶼坪': pd.DataFrame({
        'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
        'Hard_Coral': [7049.14, 0, 0, 0, 0, 0, 0, 0, 0, 182.89],
        'Soft_Coral': [501848.22, 275740.89, 276861.16, 280791.72, 279120.3, 275649.44, 277362.81, 272633.28, 279784.42, 277338.41]
    }),
}
island_names = list(island_data.keys())

# ==========================================
# 2. 共用函式 (地圖即時分類邏輯)
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
        return f"<div style='color:red'>地圖錯誤: {str(e)}</div>"

# 共用：取得特定年份的分類影像
def get_benthic_layer(year):
    start_date, end_date = f'{year}-06-01', f'{year}-09-30'
    if year >= 2019:
        s2_col = "COPERNICUS/S2_SR_HARMONIZED"
    else:
        s2_col = "COPERNICUS/S2_HARMONIZED"

    try:
        depth_raw = ee.Image('projects/ee-s1243041/assets/bathymetry_0')
        actual_band = depth_raw.bandNames().get(0)
        depth_img = depth_raw.select([actual_band]).rename('depth').clip(ROI_RECT)
        depth_mask = depth_img.lt(30).And(depth_img.gt(0))
    except:
        depth_mask = ee.Image(1).clip(ROI_RECT)

    img_train = (ee.ImageCollection(s2_col)
                    .filterBounds(ROI_RECT).filterDate('2018-01-01', '2018-12-31')
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                    .median().clip(ROI_RECT).select(['B2','B3','B4','B8']))
    
    # 修正：明確指定 kernelType='circle'
    mask_train = img_train.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask).focal_mode(radius=10, kernelType='circle', units='meters')
    
    label_img = ee.Image('ACA/reef_habitat/v2_0').clip(ROI_RECT).remap([0,11,12,13,14,15,18], [0,1,2,3,4,5,6], 0).rename('benthic').toByte()
    
    sample = img_train.updateMask(mask_train).addBands(label_img).stratifiedSample(
        numPoints=1000, classBand='benthic', region=ROI_RECT, scale=30, tileScale=8, geometries=False
    )
    classifier = ee.Classifier.smileRandomForest(50).train(sample, 'benthic', img_train.bandNames())

    target_img = (ee.ImageCollection(s2_col)
                  .filterBounds(ROI_RECT).filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                  .median().clip(ROI_RECT).select(['B2','B3','B4','B8']))
    
    target_mask = target_img.normalizedDifference(['B3', 'B8']).gt(0.1).And(depth_mask)
    
    # 修正：明確指定 kernelType='circle'
    classified = target_img.updateMask(target_mask).classify(classifier).focal_mode(radius=30, kernelType='circle', units='meters')
    
    vis = {'min': 0, 'max': 6, 'palette': ['000000', '#ffffbe', '#e0d05e', '#00ced1', '#ff69b4', '#808080', '#9bcc4f']}
    return geemap.ee_tile_layer(classified, vis, f'{year} 棲地分類')


# ==========================================
# 3. 組件：SST vs Benthic Split Map
# ==========================================
@solara.component
def SSTSplitMap(year, period_type):
    def get_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=10)
        if not ee_initialized: return save_map_to_html(m)

        def get_sst_image(y):
            start, end = (f'{y}-06-01', f'{y}-09-30') if period_type == "夏季均溫" else (f'{y}-01-01', f'{y}-12-31')
            if y < 2018:
                col = ee.ImageCollection("NASA/OCEANDATA/MODIS-Aqua/L3SMI").select('sst')
                img = col.filterBounds(ROI_RECT).filterDate(start, end).median().clip(ROI_RECT)
            else:
                col = ee.ImageCollection('JAXA/GCOM-C/L3/OCEAN/SST/V3').filter(ee.Filter.eq('SATELLITE_DIRECTION', 'D'))
                img = col.filterBounds(ROI_RECT).filterDate(start, end).median().clip(ROI_RECT).select('SST_AVE').multiply(0.0012).add(-10)
            return img

        try:
            sst_img = get_sst_image(year)
            sst_vis = {"min": 25, "max": 33, "palette": ['000000', '005aff', '43c8c8', 'fff700', 'ff0000']}
            left_layer = geemap.ee_tile_layer(sst_img, sst_vis, f'{year} 海溫')
            right_layer = get_benthic_layer(year)
            m.split_map(left_layer, right_layer)
            m.add_colorbar(sst_vis, label="海面溫度 (°C)", layer_name="SST")
            m.add_legend(title="棲地類別", labels=["沙地", "硬珊瑚", "軟珊瑚", "碎石", "海草"], colors=['#ffffbe', '#00ced1', '#ff69b4', '#808080', '#9bcc4f'])
        except Exception as e:
            return f"<div>SST 地圖載入失敗: {e}</div>"
        return save_map_to_html(m)

    map_html = solara.use_memo(get_map_html, dependencies=[year, period_type])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def SSTCoralChart():
    is_hard = coral_display_type.value == "硬珊瑚"
    current_data = hard_coral_values if is_hard else soft_coral_values
    label = "硬珊瑚" if is_hard else "軟珊瑚"
    color = 'rgba(46, 204, 113, 0.7)' if is_hard else 'rgba(155, 89, 182, 0.7)'
    with solara.Card(f"📊 關聯分析：海溫 vs {label}面積"):
        solara.ToggleButtonsSingle(value=coral_display_type, values=["硬珊瑚", "軟珊瑚"])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_mixed['Year'], y=current_data, name=f'{label}面積', marker_color=color, yaxis='y2'))
        fig.add_trace(go.Scatter(x=df_mixed['Year'], y=df_mixed['SST_Summer'], name='夏季均溫', mode='lines+markers', line=dict(color='#e74c3c', width=4)))
        fig.update_layout(title=f'環境壓力 vs {label}面積趨勢', xaxis=dict(title='年份'), yaxis=dict(title='海溫 (°C)', side='left'), yaxis2=dict(title='面積', overlaying='y', side='right', showgrid=False), legend=dict(orientation="h", y=-0.2), height=400, margin=dict(l=40, r=40, t=40, b=40))
        solara.FigurePlotly(fig)

# ==========================================
# 4. 組件：NDCI vs Benthic Split Map
# ==========================================
@solara.component
def NDCISplitMap(year):
    def get_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=11)
        if not ee_initialized: return save_map_to_html(m)

        def get_ndci_image(y):
            start, end = f'{y}-05-01', f'{y}-09-30'
            col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') if y >= 2019 else ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
            def mask(img): 
                return img.updateMask(img.select('SCL').eq(6)).divide(10000) if y >= 2019 else img.divide(10000)
            s2 = col.filterBounds(ROI_RECT).filterDate(start, end).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask)
            return s2.median().clip(ROI_RECT).normalizedDifference(['B5', 'B4']).rename('NDCI')

        try:
            ndci_img = get_ndci_image(year)
            ndci_vis = {'min': -0.05, 'max': 0.15, 'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']}
            left_layer = geemap.ee_tile_layer(ndci_img, ndci_vis, f'{year} NDCI')
            right_layer = get_benthic_layer(year)
            m.split_map(left_layer, right_layer)
            m.add_colorbar(ndci_vis, label="NDCI (優養化)", layer_name="NDCI")
            m.add_legend(title="棲地類別", labels=["沙地", "硬珊瑚", "軟珊瑚", "碎石", "海草"], colors=['#ffffbe', '#00ced1', '#ff69b4', '#808080', '#9bcc4f'])
        except Exception:
            pass
        return save_map_to_html(m)

    map_html = solara.use_memo(get_map_html, dependencies=[year])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def NDCIChart():
    is_hard = coral_display_type.value == "硬珊瑚"
    current_data = hard_coral_values if is_hard else soft_coral_values
    label = "硬珊瑚" if is_hard else "軟珊瑚"
    color = 'rgba(46, 204, 113, 0.7)' if is_hard else 'rgba(155, 89, 182, 0.7)'
    with solara.Card(f"📊 關聯分析：NDCI vs {label}面積"):
        solara.ToggleButtonsSingle(value=coral_display_type, values=["硬珊瑚", "軟珊瑚"])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_ndci['Year'], y=current_data, name=f'{label}面積', marker_color=color, yaxis='y2'))
        fig.add_trace(go.Scatter(x=df_ndci['Year'], y=df_ndci['NDCI_Mean'], name='NDCI', mode='lines+markers', line=dict(color='#00CC96', width=3)))
        fig.update_layout(title=f'優養化指標 (NDCI) vs {label}面積', xaxis=dict(title='年份'), yaxis=dict(title='NDCI', side='left'), yaxis2=dict(title='面積', overlaying='y', side='right', showgrid=False), legend=dict(orientation="h", y=-0.2), height=450, margin=dict(l=40, r=40, t=40, b=40))
        solara.FigurePlotly(fig)

# ==========================================
# 5. 組件：棘冠海星地圖 (生態疊圖)
# ==========================================
@solara.component
def StarfishHabitatMap():
    def get_starfish_map_html():
        m = geemap.Map(center=[23.25, 119.55], zoom=11)
        m.add_basemap("HYBRID")
        if not ee_initialized: return save_map_to_html(m)

        zones = [
            ee.Feature(ee.Geometry.Rectangle([119.408, 23.185, 119.445, 23.215]), {'name': '七美嶼'}),
            ee.Feature(ee.Geometry.Rectangle([119.658, 23.250, 119.680, 23.265]), {'name': '東吉嶼'}),
            ee.Feature(ee.Geometry.Rectangle([119.605, 23.245, 119.625, 23.260]), {'name': '西吉嶼'}),
            ee.Feature(ee.Geometry.Rectangle([119.510, 23.255, 119.525, 23.268]), {'name': '東嶼坪'}),
            ee.Feature(ee.Geometry.Rectangle([119.500, 23.260, 119.510, 23.272]), {'name': '西嶼坪'})
        ]
        outbreak_fc = ee.FeatureCollection(zones)

        try:
            s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(ROI_RECT).filterDate('2024-05-01', '2024-09-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)).median().clip(ROI_RECT)
            label_img = ee.Image('ACA/reef_habitat/v2_0').clip(ROI_RECT).remap([0,11,12,13,14,15,18], [0,1,2,3,4,5,6], 0).rename('benthic')
            training = s2.select(['B2','B3','B4','B8']).addBands(label_img).stratifiedSample(numPoints=1000, classBand='benthic', region=ROI_RECT, scale=30, tileScale=8, geometries=False)
            classifier = ee.Classifier.smileRandomForest(30).train(training, 'benthic', ['B2','B3','B4','B8'])
            classified = s2.classify(classifier)

            # 3:硬珊瑚(藍綠), 4:軟珊瑚(粉紅)
            coral_mask = classified.eq(3).Or(classified.eq(4))
            zone_coral = classified.updateMask(coral_mask).clipToCollection(outbreak_fc)
            coral_vis = {'min': 0, 'max': 6, 'palette': ['000000', '#ffffbe', '#e0d05e', '#00ced1', '#ff69b4', '#808080', '#9bcc4f']}

            m.addLayer(outbreak_fc.style(color='red', width=3, fillColor='00000000'), {}, "海星爆發警戒區")
            m.addLayer(zone_coral, coral_vis, "警戒區內珊瑚 (硬+軟)")
            m.add_legend(title="圖層說明", labels=["海星警戒區", "硬珊瑚", "軟珊瑚"], colors=["#FF0000", "#00CED1", "#FF69B4"])

        except Exception as e:
            m.addLayer(outbreak_fc.style(color='red', width=3, fillColor='00000000'), {}, "警戒區")

        return save_map_to_html(m)

    map_html = solara.use_memo(get_starfish_map_html, dependencies=[])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def IslandTrendChart():
    # 使用真實數據繪製
    df = island_data[selected_island.value]
    
    with solara.Card(f"📉 {selected_island.value}：歷年珊瑚面積變化"):
        solara.ToggleButtonsSingle(value=selected_island, values=island_names)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Year'], y=df['Hard_Coral'], 
            name='硬珊瑚 (Hard)', mode='lines+markers', 
            line=dict(color='#00ced1', width=4), marker=dict(size=8)
        ))
        fig.add_trace(go.Scatter(
            x=df['Year'], y=df['Soft_Coral'], 
            name='軟珊瑚 (Soft)', mode='lines+markers', 
            line=dict(color='#ff69b4', width=4), marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f"珊瑚群聚演替趨勢 ({selected_island.value})",
            xaxis=dict(title='年份', tickmode='linear'),
            yaxis=dict(title='面積 (m²)'),
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.15),
            margin=dict(l=40, r=40, t=60, b=40), height=400
        )
        solara.FigurePlotly(fig)
        solara.Info("觀察重點：數據來自 Sentinel-2 衛星影像分類運算，反映真實棲地變遷。")

# ==========================================
# 6. 組件：相關係數分析
# ==========================================
@solara.component
def CorrelationAnalysis():
    with solara.Card("📊 統計分析：皮爾森相關係數"):
        with solara.Row(gap="10px", style={"flex-wrap": "wrap", "justify-content": "center"}):
            def create_corr_heatmap(df, title, color_icon):
                corr = df.corr(method='pearson')
                fig = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale='RdBu_r', zmin=-1, zmax=1, text=corr.values.round(2), texttemplate="%{text}", showscale=False))
                fig.update_layout(title=f"{color_icon} {title}", height=280, width=300, margin=dict(l=40, r=10, t=40, b=40))
                return fig
            
            df_t = pd.DataFrame({'SST': df_mixed['SST_Summer'], 'NDCI': df_ndci['NDCI_Mean'], 'Total': total_coral_values})
            df_h = pd.DataFrame({'SST': df_mixed['SST_Summer'], 'NDCI': df_ndci['NDCI_Mean'], 'Hard': hard_coral_values})
            df_s = pd.DataFrame({'SST': df_mixed['SST_Summer'], 'NDCI': df_ndci['NDCI_Mean'], 'Soft': soft_coral_values})
            
            with solara.Column(style={"width": "310px"}):
                solara.FigurePlotly(create_corr_heatmap(df_t, "總珊瑚 (Total)", "🔵"))
            with solara.Column(style={"width": "310px"}):
                solara.FigurePlotly(create_corr_heatmap(df_h, "硬珊瑚 (Hard)", "🟢"))
            with solara.Column(style={"width": "310px"}):
                solara.FigurePlotly(create_corr_heatmap(df_s, "軟珊瑚 (Soft)", "🟣"))

        solara.Markdown("""
        **📊 數據洞察**：
        1. **硬珊瑚** 對海溫與優養化呈現顯著負相關。
        2. **軟珊瑚** 顯示較強的耐受性。
        """, style="font-size: 0.9em; background-color: #f9f9f9; padding: 10px; border-radius: 5px;")

# ==========================================
# 7. 主頁面
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "100%", "margin": "0 auto"}):
        
        solara.Markdown("# 🌊 危害澎湖珊瑚礁之各項因子監測平台")
        
        # --- 1. 海溫區塊 ---
        with solara.Card("1. 海溫異常 (SST) - 環境因子 vs 生態回應"):
            solara.Markdown("左圖：海面溫度 (SST) | 右圖：**該年** 棲地分類。")
            with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    with solara.Row():
                        solara.SliderInt(label="選擇年份", value=sst_year, min=2018, max=2025)
                        solara.ToggleButtonsSingle(value=sst_type, values=["全年平均", "夏季均溫"])
                    SSTSplitMap(sst_year.value, sst_type.value)
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    SSTCoralChart()

        # --- 2. 優養化區塊 ---
        with solara.Card("2. 海洋優養化 (NDCI) - 環境因子 vs 生態回應"):
            solara.Markdown("左圖：優養化指數 (NDCI) | 右圖：**該年** 棲地分類。")
            with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    solara.SliderInt(label="選擇年份", value=ndci_year, min=2018, max=2025)
                    NDCISplitMap(ndci_year.value)
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    NDCIChart()

        # --- 3. 棘冠海星區塊 (上圖下表) ---
        with solara.Card("3. 棘冠海星警戒區 & 珊瑚群聚結構"):
            solara.Markdown("左圖：海星警戒區內，**硬珊瑚 (藍綠)** 與 **軟珊瑚 (粉紅)** 的分佈現況。右圖：各警戒區的歷年面積趨勢。")
            
            with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "3", "min-width": "500px"}):
                    StarfishHabitatMap()
                
                with solara.Column(style={"flex": "1", "min-width": "300px"}):
                    with solara.Card(style={"background-color": "#f8f9fa"}):
                        solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%")
                        solara.Markdown("**棘冠海星**: 專吃造礁珊瑚。若無天敵控制，將導致硬珊瑚大量死亡。")
                    with solara.Details(summary="爆發原因？"):
                        solara.Markdown("1. 營養鹽增加\n2. 天敵減少\n3. 氣候變遷")

            solara.Markdown("<br>")
            IslandTrendChart()

        # --- 4. 統計分析 ---
        solara.Markdown("<br>")
        CorrelationAnalysis()

        # --- 5. 人類活動 ---
        with solara.Card("5. 人類活動影響"):
            solara.Markdown("### 海廢熱點與廢棄漁網分佈圖")
            solara.HTML(tag="iframe", attributes={"src": "https://iocean.oca.gov.tw/iOceanMap/map.aspx", "width": "100%", "height": "600px", "style": "border: none; border-radius: 8px;", "title": "海洋保育網地圖"})
            solara.Markdown("> **資料來源：** [海洋保育網 (iOcean)](https://iocean.oca.gov.tw/iOceanMap/map.aspx)")

        solara.Markdown("---")
        solara.Markdown("資料來源：NASA MODIS, JAXA GCOM-C, ESA Sentinel-2, 海洋保育署 | Update: 2025.12")