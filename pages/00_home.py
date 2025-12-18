import solara
import leafmap.leafmap as leafmap
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. 資料處理區 (只執行一次，避免網頁卡頓)
# ==========================================
csv_url = "https://raw.githubusercontent.com/Jie-Yan094/final_Penghu_coralreef/main/penghuDTM.csv"
fig_3d = None
error_msg = None

try:
    print(f"正在從 GitHub 讀取資料: {csv_url} ...")
    
    # 讀取 CSV
    z_data = pd.read_csv(csv_url)
    
    # ⚠️ 關鍵檢查：確認你的 CSV 欄位名稱
    # 假設你的欄位是 'X', 'Y', 'GRID_CODE' (如果不一樣，請修改這裡)
    if 'x' in z_data.columns and 'y' in z_data.columns and 'VALUE' in z_data.columns:
        
        # 轉換為矩陣 (Matrix)
        z_matrix = z_data.pivot(index='y', columns='x', values='VALUE')
        
        # 準備繪圖數據
        x_data = z_matrix.columns
        y_data = z_matrix.index
        z_data_matrix = z_matrix.values

        # 建立 Plotly 3D Figure
        fig_3d = go.Figure(data=[
            go.Surface(
                x=x_data,
                y=y_data,
                z=z_data_matrix,
                colorscale="Viridis", # 配色：可換 'Earth', 'Jet', 'Turbo'
                colorbar=dict(title="高程 (m)")
            )
        ])

        # 設定 3D 視圖外觀
        fig_3d.update_layout(
            title="澎湖海底地形 DEM 3D 模型",
            autosize=True,
            height=600,
            margin=dict(l=0, r=0, b=0, t=50),
            scene=dict(
                xaxis_title='經度 (X)',
                yaxis_title='緯度 (Y)',
                zaxis_title='高程 (Z)',
                aspectmode='data' # 保持真實比例，避免地形看起來過於誇張
            )
        )
        print("✅ 3D 圖表建立成功！")
        
    else:
        # 如果欄位名稱對不上，抓出目前的欄位名稱給你看
        error_msg = f"❌ 欄位名稱錯誤！你的 CSV 欄位是: {list(z_data.columns)}，程式碼需要 'X', 'Y', 'GRID_CODE'"
        print(error_msg)

except Exception as e:
    error_msg = f"❌ 資料讀取發生錯誤: {e}"
    print(error_msg)


# ==========================================
# 2. Solara 頁面組件
# ==========================================
@solara.component
def Page():
    
    # 設定最外層容器：內容置中、寬度 100%
    with solara.Column(align="center", style={"text-align": "center", "width": "100%"}):
        
        # --- 標題區塊 ---
        solara.Markdown("# 澎湖珊瑚礁與相關生態網站")

        # --- 簡介區塊 ---
        solara.Markdown("### 專案簡介")
        with solara.Column(style={"max-width": "800px"}):
            solara.Markdown(
                "澎湖島在台灣本專案運用 Google Earth Engine 的開放資料，"
                "分類與分析 2015 年至 2025 年間的衛星影像，試圖從數據中拼湊出珊瑚礁棲地的消長。"
                "這是一份關於時間、海洋與變化的故事。"
            )

        solara.Markdown("---") # 分隔線

        # --- 地圖區塊 (Leafmap) ---
        solara.Markdown("### 1. 研究區域概覽 (2D Map)")
        
        # 設定地圖容器大小
        with solara.Column(style={"height": "600px", "width": "90%", "max-width": "1000px"}):
            
            # 初始化地圖
            m = leafmap.Map(
                center=[23.52, 119.54], # 澎湖中心
                zoom=11, 
                google_map="HYBRID"     # 混合衛星圖
            )
            
            # 畫上紅框範圍
            bounds = [119.2741441721767, 23.169481136848866, 119.81144310766382, 23.87924197009108]
            m.add_bbox(bounds, color="red", weight=3, opacity=0.8, fill=False)
            
            # 顯示地圖
            solara.display(m)

        solara.Markdown("---")

        # --- 3D 地形區塊 (Plotly) ---
        solara.Markdown("### 2. 海底地形 DEM 模型 (3D View)")
        
        with solara.Column(style={"width": "90%", "max-width": "1000px", "min-height": "600px"}):
            if fig_3d:
                # 如果圖表建立成功，顯示 Plotly 元件
                solara.FigurePlotly(fig_3d)
                solara.Info("提示：您可以使用滑鼠左鍵旋轉模型，右鍵平移，滾輪縮放。")
            else:
                # 如果失敗，顯示錯誤訊息
                solara.Error(error_msg if error_msg else "無法顯示 3D 圖表，請檢查後台 Log。")

# 如果你在 Jupyter Notebook 中執行，取消下面這行的註解
# Page()
