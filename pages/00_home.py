import solara
import leafmap.leafmap as leafmap
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. 資料處理區
# ==========================================
csv_url = "https://raw.githubusercontent.com/Jie-Yan094/final_Penghu_coralreef/main/penghuDTM.csv"
fig_3d = None
error_msg = None

try:
    print(f"正在從 GitHub 讀取資料: {csv_url} ...")
    z_data = pd.read_csv(csv_url)
    
    if 'X' in z_data.columns and 'Y' in z_data.columns and 'GRID_CODE' in z_data.columns:
        
        # 1. 轉矩陣
        z_matrix = z_data.pivot(index='Y', columns='X', values='GRID_CODE')
        
        # 2. 🔴 降低解析度 (關鍵修正)
        # 為了讓瀏覽器能跑得動，我們每隔 5 點取樣一次
        # 這會大幅減少資料量，但保留地形特徵
        step = 5 
        z_matrix_small = z_matrix.iloc[::step, ::step]
        print(f"原始大小: {z_matrix.shape} -> 縮減後大小: {z_matrix_small.shape}")
        
        # 3. 準備數據
        x_data = z_matrix_small.columns
        y_data = z_matrix_small.index
        z_data_matrix = z_matrix_small.values

        # 4. 建立圖表
        fig_3d = go.Figure(data=[
            go.Surface(
                x=x_data,
                y=y_data,
                z=z_data_matrix,
                colorscale="Viridis",
                colorbar=dict(title="高程 (m)")
            )
        ])

        fig_3d.update_layout(
            title="澎湖海底地形 DEM 3D 模型",
            autosize=True, # 讓它自動填滿容器
            margin=dict(l=0, r=0, b=0, t=50),
            scene=dict(
                xaxis_title='經度',
                yaxis_title='緯度',
                zaxis_title='高程',
                aspectmode='data'
            )
        )
        print("✅ 3D 圖表建立成功！")
        
    else:
        error_msg = f"❌ 欄位名稱錯誤！csv 欄位是: {list(z_data.columns)}"
        print(error_msg)

except Exception as e:
    error_msg = f"❌ 資料讀取發生錯誤: {e}"
    print(error_msg)


# ==========================================
# 2. 頁面組件
# ==========================================
@solara.component
def Page():
    
    with solara.Column(align="center", style={"text-align": "center", "width": "100%"}):
        
        solara.Markdown("# 澎湖珊瑚礁與相關生態網站")

        solara.Markdown("### 專案簡介")
        with solara.Column(style={"max-width": "800px"}):
            solara.Markdown(
                "澎湖島在台灣本專案運用 Google Earth Engine 的開放資料，"
                "分類與分析 2015 年至 2025 年間的衛星影像，試圖從數據中拼湊出珊瑚礁棲地的消長。"
                "這是一份關於時間、海洋與變化的故事。"
            )

        solara.Markdown("---")

        # --- 地圖區塊 ---
        solara.Markdown("### 1. 研究區域概覽")
        with solara.Column(style={"height": "600px", "width": "90%", "max-width": "1000px"}):
            m = leafmap.Map(center=[23.52, 119.54], zoom=11, google_map="HYBRID")
            bounds = [119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108]
            m.add_bbox(bounds, color="red", weight=3, opacity=0.8, fill=False)
            solara.display(m)

        solara.Markdown("---")

        # --- 3D 地形區塊 ---
        solara.Markdown("### 2. 海底地形 DEM 模型")
        
        # 🔴 強制設定高度，確保圖表有空間顯示
        with solara.Column(style={"width": "90%", "max-width": "1000px", "height": "700px"}):
            if fig_3d:
                solara.FigurePlotly(fig_3d)
                solara.Info("提示：滑鼠左鍵旋轉，右鍵平移，滾輪縮放。")
            else:
                solara.Error(error_msg if error_msg else "無法顯示 3D 圖表")