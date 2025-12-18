import solara
import leafmap.leafmap as leafmap
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. 資料處理區 (增強除錯版)
# ==========================================
csv_url = "https://raw.githubusercontent.com/Jie-Yan094/final_Penghu_coralreef/main/penghuDTM.csv"
fig_3d = None
error_msg = None

try:
    print(f"正在讀取: {csv_url} ...")
    z_data = pd.read_csv(csv_url)
    
    # 檢查欄位是否存在
    if 'x' in z_data.columns and 'y' in z_data.columns and 'VALUE' in z_data.columns:
        
        # 🛠️ 修正 1：強制將資料轉為「數字」，避免讀成文字
        z_data['x'] = pd.to_numeric(z_data['x'], errors='coerce')
        z_data['y'] = pd.to_numeric(z_data['y'], errors='coerce')
        z_data['VALUE'] = pd.to_numeric(z_data['VALUE'], errors='coerce')

        # 移除轉型失敗的髒資料 (NaN)
        z_data = z_data.dropna()

        # 🛠️ 修正 2：先對座標進行排序，這對 pivot 很重要
        z_data = z_data.sort_values(by=['y', 'x'])

        # 轉換為矩陣
        z_matrix = z_data.pivot(index='y', columns='x', values='VALUE')
        
        # 🛠️ 修正 3：填補矩陣中的空洞 (因為不是每個網格點都有衛星資料)
        # 用 0 或平均值填補，這裡用線性插值會比較漂亮，但先用 0 確保能畫出來
        z_matrix = z_matrix.fillna(0) 

        # 降低解析度 (每 5 點取 1 點)，避免網頁跑不動
        step = 5 
        z_matrix_small = z_matrix.iloc[::step, ::step]
        
        print(f"矩陣形狀 (Shape): {z_matrix_small.shape}")
        print(f"數值範圍: Min={z_matrix_small.values.min()}, Max={z_matrix_small.values.max()}")

        if z_matrix_small.size == 0:
            raise ValueError("矩陣為空，可能是因為座標 X, Y 無法對齊成網格")

        # 準備繪圖數據
        x_data = z_matrix_small.columns
        y_data = z_matrix_small.index
        z_data_matrix = z_matrix_small.values

        # 建立圖表
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
            title="澎湖地形 DEM 3D 模型",
            autosize=True,
            margin=dict(l=0, r=0, b=0, t=50),
            scene=dict(
                xaxis_title='經度',
                yaxis_title='緯度',
                zaxis_title='高程',
                aspectmode='manual',  # 手動調整比例，避免看起來扁扁的
                aspectratio=dict(x=1, y=1, z=0.5) 
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
        solara.Markdown("### 2. 地形 DEM 模型")
        
        # 🔴 強制設定高度，確保圖表有空間顯示
        with solara.Column(style={"width": "90%", "max-width": "1000px", "height": "700px"}):
            if fig_3d:
                solara.FigurePlotly(fig_3d)
                solara.Info("提示：滑鼠左鍵旋轉，右鍵平移，滾輪縮放。")
            else:
                solara.Error(error_msg if error_msg else "無法顯示 3D 圖表")