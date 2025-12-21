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
# 0. GEE 驗證與初始化 (穩健版)
# ==========================================
ee_initialized = False # 標記 GEE 是否成功啟動

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
            print(f"⚠️ Token 解析或驗證失敗: {e}，嘗試使用本機驗證...")
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
# 1. 資料準備 (硬珊瑚數據)
# ==========================================
ROI_RECT = ee.Geometry.Rectangle([119.2741, 23.1695, 119.8114, 23.8792])
ROI_CENTER = [23.5, 119.5]

selected_year = solara.reactive(2024)

years_list = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
hard_coral_values = [342.08, 92.92, 1584.55, 382.45, 76.97, 197.21, 95.55, 224.21, 239.71, 1264.49]
df_benthic = pd.DataFrame({'Year': years_list, 'Hard_Coral_Area': hard_coral_values})

# ==========================================
# 2. 地圖組件 (已修復 Map Error 顯示)
# ==========================================
def save_map_to_html(m):
    try:
        # 使用 delete=False 確保檔案在讀取前不會被刪除
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            temp_path = tmp.name
        
        m.to_html(filename=temp_path)
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 讀取完畢後手動刪除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return html_content
    except Exception as e:
        # 🔴 關鍵修改：顯示具體錯誤訊息，而不是只顯示 "Map Error"
        return f"<div style='color:red; padding:10px; border:1px solid red;'>Map Rendering Error: {str(e)}</div>"

@solara.component
def BenthicMap(year):
    def get_map_html():
        m = geemap.Map(center=ROI_CENTER, zoom=11)
        m.add_basemap("HYBRID")
        
        # 只有在 GEE 成功初始化時才加入圖層，避免報錯
        if ee_initialized:
            try:
                # 顯示 ROI 框
                m.addLayer(ROI_RECT, {'color': 'yellow', 'fillColor': '00000000'}, "澎湖群島 ROI")
                
                # 嘗試載入 Sentinel-2 (範例)
                # start_date = f'{year}-06-01'
                # end_date = f'{year}-09-30'
                # s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(ROI_RECT).filterDate(start_date, end_date).median().clip(ROI_RECT)
                # m.addLayer(s2, {'min':0, 'max':3000, 'bands':['B4','B3','B2']}, f"{year} 衛星影像")
                
            except Exception as e:
                print(f"圖層加入失敗: {e}")
        
        return save_map_to_html(m)

    map_html = solara.use_memo(get_map_html, dependencies=[year])
    return solara.HTML(tag="iframe", attributes={"srcDoc": map_html, "width": "100%", "height": "600px", "style": "border:none;"})

# ==========================================
# 3. 圖表組件
# ==========================================
@solara.component
def HardCoralChart():
    with solara.Card("📊 硬珊瑚面積變化趨勢 (Hard Coral Area)"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_benthic['Year'], 
            y=df_benthic['Hard_Coral_Area'],
            mode='lines+markers+text',
            name='硬珊瑚面積',
            line=dict(color='#2ecc71', width=4),
            marker=dict(size=10, color='#27ae60'),
            text=df_benthic['Hard_Coral_Area'].round(0),
            textposition="top center"
        ))
        fig.update_layout(
            title='歷年硬珊瑚覆蓋面積 (m²)',
            xaxis=dict(title='年份', tickmode='linear'),
            yaxis=dict(title='面積 (平方公尺)'),
            hovermode="x unified",
            margin=dict(l=40, r=40, t=60, b=40),
            height=400
        )
        solara.FigurePlotly(fig)

# ==========================================
# 4. 主頁面
# ==========================================
@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "100%", "margin": "0 auto"}):
        
        solara.Markdown("# 🪸 澎湖珊瑚礁棲地動態監測系統 (Benthic Habitat)")
        
        # 顯示系統狀態，方便除錯
        status_color = "green" if ee_initialized else "red"
        status_text = "GEE 連線正常" if ee_initialized else "GEE 連線失敗 (僅顯示基礎圖表)"
        solara.Markdown(f"**系統狀態**: <span style='color:{status_color}'>{status_text}</span>")

        with solara.Row(gap="30px", style={"flex-wrap": "wrap"}):
            
            # --- 左側：地圖 ---
            with solara.Column(style={"flex": "1", "min-width": "500px"}):
                with solara.Card("1. 底質分類地圖"):
                    solara.Markdown("透過衛星影像與機器學習，辨識珊瑚礁、沙地、岩石等底質分佈。")
                    solara.SliderInt(label="選擇年份", value=selected_year, min=2016, max=2025)
                    BenthicMap(selected_year.value)
                    if not ee_initialized:
                        solara.Warning("注意：因 GEE 未連線，目前僅顯示底圖，無法載入衛星圖層。")

            # --- 右側：統計數據 ---
            with solara.Column(style={"flex": "1", "min-width": "500px"}):
                with solara.Row(gap="10px"):
                    current_area = df_benthic[df_benthic['Year'] == 2025]['Hard_Coral_Area'].values[0]
                    avg_area = df_benthic['Hard_Coral_Area'].mean()
                    solara.Card(f"{current_area:.0f} m²", "2025 硬珊瑚面積", style={"background": "#e8f5e9", "flex": "1"})
                    solara.Card(f"{avg_area:.0f} m²", "10年平均面積", style={"background": "#f1f8e9", "flex": "1"})

                HardCoralChart()
                
                with solara.Card("🔍 棲地狀態解讀"):
                    solara.Markdown("""
                    * **硬珊瑚 (Hard Coral)**：造礁珊瑚是健康的指標。
                    * **趨勢分析**：
                        * 2018 與 2025 年觀測到較高的面積數值。
                        * 2017 與 2020 年面積顯著低落，可能受當年颱風或極端氣候影響。
                    """)

        solara.Markdown("---")
        solara.Markdown("Data Source: Sentinel-2 & Ecological Survey | Powered by Solara & GEE")