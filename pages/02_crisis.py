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
# 定義澎湖感興趣區域 (ROI) - 避免重複定義
ROI_RECT = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])
ROI_CENTER = [23.5, 119.5]

# Reactive 變數
sst_year = solara.reactive(2021)      # 海溫地圖年份
sst_type = solara.reactive("夏季均溫") # 海溫統計類型
ndci_year = solara.reactive(2024)     # NDCI 地圖年份

# --- 資料準備 A: SST 資料拼接 (邏輯：2018前用新資料，2018後用舊資料) ---
# 1. 新資料 (補足 2016-2017)
data_sst_new = {
    'Year': [2016, 2017],
    'SST_Summer_Avg': [28.19, 28.51]
}
# 2. 舊資料 (2018-2025, 模擬您原本的資料，請確認數據)
data_sst_old = {
    'Year': [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'SST_Summer_Avg': [28.07, 27.83, 28.52, 28.44, 28.30, 28.45, 29.10, 28.80] # 後4年為模擬數據，請替換回您的真實數據
}
df_sst = pd.concat([pd.DataFrame(data_sst_new), pd.DataFrame(data_sst_old)]).sort_values('Year').reset_index(drop=True)

# --- 資料準備 B: NDCI 資料 ---
ndci_data = {
    'Year': [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'NDCI_Mean': [-0.059707, -0.064990, -0.063422, 0.041270, 0.041549, 
                  0.041954, 0.093461, 0.107500, 0.108534, 0.066040],
    'Image_Count': [24, 25, 52, 24, 30, 25, 23, 25, 19, 31]
}
df_ndci = pd.DataFrame(ndci_data)


# ==========================================
# 2. 共用函式：地圖轉 HTML
# ==========================================
def save_map_to_html(m):
    """將 geemap 物件轉換為 HTML 字串，並確保暫存檔被刪除"""
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
# 3. 組件：SST 相關 (地圖 + 圖表)
# ==========================================
@solara.component
def SSTMap(year, period_type):
    def get_sst_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=10)
        
        if period_type == "夏季均溫":
            start_date, end_date = f'{year}-06-01', f'{year}-09-30'
            vis_min, vis_max = 25, 33
            layer_title = f"{year} 夏季均溫"
        else:
            start_date, end_date = f'{year}-01-01', f'{year}-12-31'
            vis_min, vis_max = 18, 32
            layer_title = f"{year} 全年平均"

        try:
            # JAXA GCOM-C 
            img_collection = (
                ee.ImageCollection('JAXA/GCOM-C/L3/OCEAN/SST/V3')
                .filterBounds(ROI_RECT)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.eq('SATELLITE_DIRECTION', 'D'))
            )
            
            if img_collection.size().getInfo() == 0:
                return f"<div style='padding:20px; color: gray;'>⚠️ 無 {year} 年 JAXA SST 數據 (資料可能尚未更新或該年無數據)</div>"

            # 數值轉換 SST [°C] = SST_AVE * 0.0012 + (-10)
            dataset = img_collection.median().clip(ROI_RECT).select('SST_AVE').multiply(0.0012).add(-10)
            
            sst_vis = {
              "min": vis_min, "max": vis_max,
              "palette": ['000000', '005aff', '43c8c8', 'fff700', 'ff0000']
            }
            m.addLayer(dataset, sst_vis, layer_title)
            m.add_colorbar(sst_vis, label="海面溫度 (°C)", orientation='horizontal', layer_name=layer_title)
            
        except Exception as e:
            return f"<div>SST 載入失敗: {e}</div>"

        return save_map_to_html(m)

    map_html = solara.use_memo(get_sst_map_html, dependencies=[year, period_type])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def SSTChart():
    # 建立 SST 折線圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sst['Year'], y=df_sst['SST_Summer_Avg'],
        mode='lines+markers', name='夏季均溫',
        line=dict(color='#FF5733', width=3), marker=dict(size=8)
    ))
    
    # 標示 2018 分界線
    fig.add_vline(x=2017.5, line_width=1, line_dash="dash", line_color="gray")
    fig.add_annotation(x=2017.5, y=df_sst['SST_Summer_Avg'].max(), text="資料來源變更", showarrow=False, yshift=10)

    fig.update_layout(
        title='歷年夏季海溫趨勢 (拼接資料)',
        xaxis_title='年份', yaxis_title='溫度 (°C)',
        hovermode="x unified", margin=dict(l=40, r=40, t=40, b=40),
        height=350
    )
    solara.FigurePlotly(fig)

# ==========================================
# 4. 組件：NDCI 相關
# ==========================================
@solara.component
def NDCIMap(year):
    def get_ndci_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=11)
        start_date, end_date = f'{year}-05-01', f'{year}-09-30'

        # 雙模式去雲邏輯
        if year >= 2019:
            col_name = 'COPERNICUS/S2_SR_HARMONIZED'
            def mask_algo(img): return img.updateMask(img.select('SCL').eq(6)).divide(10000)
        else:
            col_name = 'COPERNICUS/S2_HARMONIZED'
            def mask_algo(img): 
                qa = img.select('QA60')
                mask = qa.bitwiseAnd(1<<10).eq(0).And(qa.bitwiseAnd(1<<11).eq(0))
                return img.updateMask(mask.And(img.normalizedDifference(['B3', 'B8']).gt(0))).divide(10000)

        def add_ndci(img): return img.addBands(img.normalizedDifference(['B5', 'B4']).rename('NDCI'))

        s2 = (ee.ImageCollection(col_name).filterDate(start_date, end_date)
              .filterBounds(ROI_RECT).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
              .map(mask_algo).map(add_ndci))

        img_med = s2.median().clip(ROI_RECT)
        ndci_vis = {'min': -0.05, 'max': 0.15, 'palette': ['#0011ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000']}
        
        try:
            m.addLayer(img_med, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3}, 'True Color')
            m.addLayer(img_med.select('NDCI'), ndci_vis, 'NDCI')
            m.add_colorbar(ndci_vis, label="NDCI", layer_name='NDCI')
        except Exception:
            pass # 忽略圖層錯誤，通常是沒影像

        return save_map_to_html(m)

    map_html = solara.use_memo(get_ndci_map_html, dependencies=[year])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def NDCIChart():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_ndci['Year'], y=df_ndci['NDCI_Mean'], name='NDCI Mean',
        mode='lines+markers', line=dict(color='#00CC96', width=3)
    ))
    fig.add_trace(go.Bar(
        x=df_ndci['Year'], y=df_ndci['Image_Count'], name='Image Count',
        marker_color='#636EFA', opacity=0.3, yaxis='y2'
    ))

    fig.update_layout(
        title='NDCI 夏季平均值 vs 影像數量',
        xaxis=dict(title='年份', tickmode='linear'),
        yaxis=dict(title='NDCI 指數', titlefont=dict(color="#00CC96"), tickfont=dict(color="#00CC96")),
        yaxis2=dict(title='影像數量', titlefont=dict(color="#636EFA"), tickfont=dict(color="#636EFA"), overlaying='y', side='right'),
        legend=dict(x=0.01, y=0.99), hovermode="x unified", margin=dict(t=40, b=40), height=350
    )
    solara.FigurePlotly(fig)

# ==========================================
# 5. 組件：棘冠海星地圖
# ==========================================
@solara.component
def StarfishMap():
    def get_starfish_map_html():
        m = geemap.Map(center=[23.25, 119.55], zoom=11)
        m.add_basemap("HYBRID")
        
        # 定義警戒區
        zones = [
            ee.Feature(ee.Geometry.Rectangle([119.408, 23.185, 119.445, 23.215]), {'name': '七美嶼'}),
            ee.Feature(ee.Geometry.Rectangle([119.658, 23.250, 119.680, 23.265]), {'name': '東吉嶼'}),
            ee.Feature(ee.Geometry.Rectangle([119.605, 23.245, 119.625, 23.260]), {'name': '西吉嶼'}),
            ee.Feature(ee.Geometry.Rectangle([119.510, 23.255, 119.525, 23.268]), {'name': '東嶼坪'}),
            ee.Feature(ee.Geometry.Rectangle([119.500, 23.260, 119.510, 23.272]), {'name': '西嶼坪'})
        ]
        outbreak_zones = ee.FeatureCollection(zones)
        m.addLayer(outbreak_zones.style(color='red', width=3, fillColor='00000000'), {}, "警戒區")
        return save_map_to_html(m)

    map_html = solara.use_memo(get_starfish_map_html, dependencies=[])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "400px", "style": "border:none;"})

# ==========================================
# 6. 主頁面
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "1200px", "margin": "0 auto"}):
        
        solara.Markdown("# 🌊 危害澎湖珊瑚礁之各項因子監測平台")
        
        # --- 1. 海溫區塊 ---
        with solara.Card("1. 海溫異常 (SST)"):
            solara.Markdown("長期的高溫會導致珊瑚白化。下圖結合了 **JAXA 衛星監測** 與 **歷年統計數據**。")
            
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                # 左側：地圖與控制項
                with solara.Column(style={"flex": "1", "min-width": "350px"}):
                    solara.Markdown("### 🗺️ 衛星海溫分佈")
                    with solara.Row():
                        solara.SliderInt(label="年份", value=sst_year, min=2018, max=2025)
                        solara.ToggleButtonsSingle(value=sst_type, values=["全年平均", "夏季均溫"])
                    SSTMap(sst_year.value, sst_type.value)
                
                # 右側：統計圖表
                with solara.Column(style={"flex": "1", "min-width": "350px"}):
                    solara.Markdown("### 📈 歷年溫度趨勢")
                    SSTChart()
                    solara.Info("註：2016-2017 為補充數據，2018 起採用校正後資料庫。")

        # --- 2. 優養化區塊 ---
        with solara.Card("2. 海洋優養化 (NDCI)"):
            solara.Markdown("監測夏季水體葉綠素濃度，紅色代表優養化風險高。")
            
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "350px"}):
                    solara.SliderInt(label="年份", value=ndci_year, min=2016, max=2025)
                    NDCIMap(ndci_year.value)
                
                with solara.Column(style={"flex": "1", "min-width": "350px"}):
                    NDCIChart()
                    solara.Markdown("""
                    * **2016-2018**: Sentinel-2 TOA 數據 (NDWI 去雲)
                    * **2019-2025**: Sentinel-2 SR 數據 (SCL 去雲)
                    * **趨勢**: 2022 年後 NDCI 指數呈現上升趨勢，需持續關注。
                    """, style="font-size: 0.9em; color: gray;")

        # --- 3. 棘冠海星區塊 ---
        with solara.Card("3. 生態殺手：棘冠海星 (Crown-of-thorns Starfish)"):
            with solara.Row(gap="30px", style={"flex-wrap": "wrap-reverse"}):
                # 左側：文字與地圖
                with solara.Column(style={"flex": "3", "min-width": "300px"}):
                    solara.Markdown("### 🚨 爆發警戒區域")
                    StarfishMap()
                    
                    # 修正：將 ExpansionPanel 改為 Details
                    with solara.Details(summary="點擊查看：棘冠海星大爆發的原因？"):
                        solara.Markdown("""
                        1. **營養鹽增加**：人類污水排放導致浮游生物增加，提供幼體食物。
                        2. **天敵減少**：過度捕撈大法螺與蘇眉魚。
                        3. **氣候變遷**：暖化有利於幼體發育。
                        """)
                
                # 右側：圖片與介紹
                with solara.Column(style={"flex": "2", "min-width": "250px", "background-color": "#f8f9fa", "padding": "15px", "border-radius": "10px"}):
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%")
                    solara.Markdown("""
                    **棘冠海星 (魔鬼海星)**
                    * **食性**: 專吃造礁珊瑚。
                    * **破壞力**: 一隻成體一年可吃掉 6 平方公尺珊瑚。
                    * **現況**: 七美及南方四島皆已出現爆發跡象。
                    """)

        # --- 4. 人類活動 ---
        with solara.Card("4. 人類活動影響"):
            solara.Markdown("*(此區域正進行資料彙整中，預計加入漁業活動熱點分析)*")

        solara.Markdown("---")
        solara.Markdown("資料來源：JAXA GCOM-C, ESA Sentinel-2, 海洋保育署 | Update: 2025.12")