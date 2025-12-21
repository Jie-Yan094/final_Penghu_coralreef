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

# --- 資料準備 A: 整合數據 ---
years_list = [ 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

# 1. 夏季海溫 (SST)
sst_values = [
    28.16, 27.75, 28.62, 28.37, 28.29, # 2018-2022
    28.02, 28.95, 28.43  # 2023-2025
]

# 2. 珊瑚礁面積數據 (兩組)
# A. 總珊瑚 (硬+軟)
total_coral_values = [
    28606.5, 40291.9, 13151.8, 
    22949.0, 15740.7, 25286.3, 42849.9, 27761.9
]
# B. 硬珊瑚 (Hard Coral Only)
hard_coral_values = [
    1584.55, 382.45, 76.97, 
    197.21, 95.55, 224.21, 239.71, 1264.49
]


# 建立主要 DataFrame (主圖表預設使用 硬珊瑚)
df_mixed = pd.DataFrame({
    'Year': years_list,
    'SST_Summer': sst_values,
    'Coral_Area': hard_coral_values,    # 用於 SST 圖表 (綠色柱狀)
    'Coral_Total': total_coral_values   # 保留備用
})

# --- 資料準備 B: NDCI 資料 ---
ndci_data = {
    'Year': [ 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'NDCI_Mean': [ -0.063422, 0.041270, 0.041549, 
                  0.041954, 0.093461, 0.107500, 0.108534, 0.066040],
    'Image_Count': [ 52, 24, 30, 25, 23, 25, 19, 31]
}
df_ndci = pd.DataFrame(ndci_data)

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
# 3. 組件：SST 相關
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
            if year < 2018:
                source_name = "NASA MODIS-Aqua"
                img_collection = (
                    ee.ImageCollection("NASA/OCEANDATA/MODIS-Aqua/L3SMI")
                    .filterBounds(ROI_RECT).filterDate(start_date, end_date).select('sst')
                )
                dataset = img_collection.median().clip(ROI_RECT)
            else:
                source_name = "JAXA GCOM-C"
                img_collection = (
                    ee.ImageCollection('JAXA/GCOM-C/L3/OCEAN/SST/V3')
                    .filterBounds(ROI_RECT).filterDate(start_date, end_date)
                    .filter(ee.Filter.eq('SATELLITE_DIRECTION', 'D'))
                )
                dataset = img_collection.median().clip(ROI_RECT).select('SST_AVE').multiply(0.0012).add(-10)

            if img_collection.size().getInfo() == 0:
                return f"<div style='padding:20px; color: gray;'>⚠️ 無 {year} 年 {source_name} 數據</div>"

            sst_vis = {"min": vis_min, "max": vis_max, "palette": ['000000', '005aff', '43c8c8', 'fff700', 'ff0000']}
            full_title = f"{layer_title} ({source_name})"
            m.addLayer(dataset, sst_vis, full_title)
            m.add_colorbar(sst_vis, label="海面溫度 (°C)", orientation='horizontal', layer_name=full_title)
            
        except Exception as e:
            return f"<div>SST 地圖載入失敗: {e}</div>"

        return save_map_to_html(m)

    map_html = solara.use_memo(get_sst_map_html, dependencies=[year, period_type])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def SSTCoralChart():
    with solara.Card("📊 關聯分析：海溫 vs 硬珊瑚面積"):
        fig = go.Figure()
        # 硬珊瑚
        fig.add_trace(go.Bar(
            x=df_mixed['Year'], y=df_mixed['Coral_Area'], name='硬珊瑚面積 (m²)',
            marker_color='rgba(46, 204, 113, 0.6)', yaxis='y2'
        ))
        # 海溫
        fig.add_trace(go.Scatter(
            x=df_mixed['Year'], y=df_mixed['SST_Summer'], name='夏季均溫 (°C)',
            mode='lines+markers', line=dict(color='#e74c3c', width=4),
            marker=dict(size=10, color='#c0392b', symbol='circle')
        ))

        fig.update_layout(
            title='環境壓力 vs 硬珊瑚面積趨勢',
            xaxis=dict(title='年份', tickmode='linear', dtick=1),
            yaxis=dict(title=dict(text='海面溫度 (°C)', font=dict(color="#e74c3c")), tickfont=dict(color="#e74c3c"), range=[27, 29.5], side='left'),
            yaxis2=dict(title=dict(text='硬珊瑚面積 (m²)', font=dict(color="#2ecc71")), tickfont=dict(color="#2ecc71"), overlaying='y', side='right', showgrid=False, range=[0, 2000]),
            legend=dict(x=0.5, y=-0.15, xanchor='center', orientation="h"),
            hovermode="x unified", margin=dict(l=50, r=50, t=60, b=80), height=500, autosize=True
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
            pass 
        return save_map_to_html(m)

    map_html = solara.use_memo(get_ndci_map_html, dependencies=[year])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

@solara.component
def NDCIChart():
    with solara.Card("📊 關聯分析：NDCI vs 硬珊瑚面積"):
        fig = go.Figure()
        # 硬珊瑚
        fig.add_trace(go.Bar(
            x=df_ndci['Year'], y=hard_coral_values, name='硬珊瑚面積 (m²)',
            marker_color='rgba(46, 204, 113, 0.6)', yaxis='y2'
        ))
        # NDCI
        fig.add_trace(go.Scatter(
            x=df_ndci['Year'], y=df_ndci['NDCI_Mean'], name='NDCI (優養化指標)',
            mode='lines+markers', line=dict(color='#00CC96', width=3), marker=dict(size=8)
        ))

        fig.update_layout(
            title='優養化指標 (NDCI) vs 硬珊瑚面積',
            xaxis=dict(title='年份', tickmode='linear', dtick=1),
            yaxis=dict(title=dict(text='NDCI 指數', font=dict(color="#00CC96")), tickfont=dict(color="#00CC96"), side='left'),
            yaxis2=dict(title=dict(text='硬珊瑚面積 (m²)', font=dict(color="#2ecc71")), tickfont=dict(color="#2ecc71"), overlaying='y', side='right', showgrid=False, range=[0, 2000]),
            legend=dict(x=0.5, y=-0.15, xanchor='center', orientation="h"),
            hovermode="x unified", margin=dict(l=50, r=50, t=50, b=80), height=500, autosize=True
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
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "500px", "style": "border:none;"})

# ==========================================
# 6. 組件：相關係數分析 (雙重對照版)
# ==========================================
@solara.component
def CorrelationAnalysis():
    with solara.Card("🧮 統計分析：皮爾森相關係數 (總面積 vs 硬珊瑚)"):
        
        with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
            
            # --- 左欄：總珊瑚面積 ---
            with solara.Column(style={"flex": "1", "min-width": "400px"}):
                solara.Markdown("### 🔵 總珊瑚面積 (Total)")
                
                df_total = pd.DataFrame({
                    '夏季海溫 (SST)': df_mixed['SST_Summer'],
                    '優養化 (NDCI)': df_ndci['NDCI_Mean'],
                    '總珊瑚面積': total_coral_values
                })
                corr_total = df_total.corr(method='pearson')
                
                fig_t = go.Figure(data=go.Heatmap(
                    z=corr_total.values, x=corr_total.columns, y=corr_total.index,
                    colorscale='RdBu_r', zmin=-1, zmax=1,
                    text=corr_total.values.round(2), texttemplate="%{text}", textfont={"size": 16}
                ))
                fig_t.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
                solara.FigurePlotly(fig_t)

            # --- 右欄：硬珊瑚面積 ---
            with solara.Column(style={"flex": "1", "min-width": "400px"}):
                solara.Markdown("### 🟢 硬珊瑚面積 (Hard Only)")
                
                df_hard = pd.DataFrame({
                    '夏季海溫 (SST)': df_mixed['SST_Summer'],
                    '優養化 (NDCI)': df_ndci['NDCI_Mean'],
                    '硬珊瑚面積': hard_coral_values
                })
                corr_hard = df_hard.corr(method='pearson')
                
                fig_h = go.Figure(data=go.Heatmap(
                    z=corr_hard.values, x=corr_hard.columns, y=corr_hard.index,
                    colorscale='RdBu_r', zmin=-1, zmax=1,
                    text=corr_hard.values.round(2), texttemplate="%{text}", textfont={"size": 16}
                ))
                fig_h.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
                solara.FigurePlotly(fig_h)

        # 簡單洞察
        solara.Markdown("""
        **📊 比較洞察**：
        * 夏季海溫 (SST) vs 總珊瑚礁面積：-0.15 / 硬珊瑚面積：-0.18 : 雖然呈現出的相關度數值較低，但仍顯示出海溫升高對珊瑚健康的負面影響。
        * 優養化指標 (NDCI) vs 總珊瑚面積：+0.19 / 硬珊瑚面積：-0.29 : 優養化對總珊瑚似乎有輕微正面影響，但對硬珊瑚則有明顯負面影響，顯示不同珊瑚類型對環境壓力的反應不同。
        * **硬珊瑚** 對海溫(SST)與優養化指標(NDCI)的負相關程度應比總珊瑚更明顯，因為軟珊瑚耐受性較高，可能會稀釋環境壓力的訊號。
        """, style="font-size: 0.9em; color: gray;")

# ==========================================
# 7. 主頁面
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "100%", "margin": "0 auto"}):
        
        solara.Markdown("# 🌊 危害澎湖珊瑚礁之各項因子監測平台")
        
        # --- 1. 海溫區塊 ---
        with solara.Card("1. 海溫異常 (SST)"):
            solara.Markdown("長期的高溫會導致珊瑚白化。下圖結合了 **衛星監測** 與 **珊瑚礁生態調查**。")
            solara.Markdown("(地圖到時候想換成跟分類做Split Screen Map 比較，不過先放這個版本。)")
            with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    solara.Markdown("### 🗺️ 衛星海溫分佈")
                    with solara.Row():
                        solara.SliderInt(label="年份", value=sst_year, min=2016, max=2025)
                        solara.ToggleButtonsSingle(value=sst_type, values=["全年平均", "夏季均溫"])
                    source_hint = "NASA MODIS" if sst_year.value < 2018 else "JAXA GCOM-C"
                    solara.Markdown(f"*資料來源: **{source_hint}*** (解析度差異為衛星特性)", style="font-size: 12px; color: gray; margin-top: -10px;")
                    SSTMap(sst_year.value, sst_type.value)
                
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    solara.Markdown("### 📈 環境 vs 生態 (硬珊瑚)")
                    SSTCoralChart()

        # --- 2. 優養化區塊 ---
        with solara.Card("2. 海洋優養化 (NDCI)"):
            solara.Markdown("監測夏季水體葉綠素濃度，紅色代表優養化風險高。")
            solara.Markdown("(這裡也想分類做Split Screen Map 比較，先放這個版本。)")
            with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    solara.SliderInt(label="年份", value=ndci_year, min=2016, max=2025)
                    NDCIMap(ndci_year.value)
                
                with solara.Column(style={"flex": "1", "min-width": "500px"}):
                    NDCIChart()

        # --- 3. 棘冠海星區塊 ---
        with solara.Card("3. 好餓好餓的珊瑚礁大胃王--棘冠海星 (Crown-of-thorns Starfish)"):
            solara.Markdown("這裡想把分類跟這些區域疊再一起顯示，並計算各區域每年硬珊瑚面積")
            with solara.Row(gap="30px", style={"flex-wrap": "wrap-reverse"}):
                with solara.Column(style={"flex": "3", "min-width": "500px"}):
                    solara.Markdown("### 🚨 爆發警戒區域")
                    StarfishMap()
                    with solara.Details(summary="點擊查看：棘冠海星大爆發的原因？"):
                        solara.Markdown("1. 營養鹽增加\n2. 天敵減少\n3. 氣候變遷")
                
                with solara.Column(style={"flex": "2", "min-width": "400px", "background-color": "#f8f9fa", "padding": "15px", "border-radius": "10px"}):
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%")
                    solara.Markdown("**棘冠海星**: 專吃造礁珊瑚，現況七美及南方四島皆已出現爆發跡象。")

        # --- 4. 統計分析 ---
        solara.Markdown("<br>")
        CorrelationAnalysis()

        # --- 5. 人類活動 ---
        with solara.Card("5. 人類活動影響"):
            solara.Markdown("### 海廢熱點與廢棄漁網分佈圖")
            
            # 使用 solara.HTML 嵌入 iOcean 地圖小工具
            # 注意：如果該網站禁止 IFrame 嵌入，此處會顯示空白或拒絕連線
            solara.HTML(tag="iframe", attributes={
                "src": "https://iocean.oca.gov.tw/iOceanMap/map.aspx",
                "width": "100%",
                "height": "600px",
                "style": "border: none; border-radius: 8px;",
                "title": "海洋保育網地圖"
            })
            
            # 根據資料開放宣告，必須註明出處
            solara.Markdown("""
            > **資料來源：** [海洋委員會海洋保育署 - 海洋保育網 (iOcean)](https://iocean.oca.gov.tw/iOceanMap/map.aspx)  
            > *本圖資依據政府資料開放授權條款利用。*
            """)

        solara.Markdown("---")
        solara.Markdown("資料來源：NASA MODIS, JAXA GCOM-C, ESA Sentinel-2, 海洋保育署 | Update: 2025.12")