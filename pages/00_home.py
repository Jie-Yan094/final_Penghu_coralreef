import solara
import leafmap.leafmap as leafmap
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. 資料處理區
# ==========================================
# 確保這是正確的 Raw 連結
csv_url = "https://raw.githubusercontent.com/Jie-Yan094/final_Penghu_coralreef/main/penghuDTM.csv"
fig_3d = None
error_msg = None

try:
    print(f"正在讀取: {csv_url} ...")
    z_data = pd.read_csv(csv_url)
    
    # ⚠️ 請確認你的 CSV 欄位名稱是否真的是小寫 'x', 'y' 和大寫 'VALUE'
    # 如果是 'X', 'Y', 'GRID_CODE'，請自行修改下面這行
    col_x = 'x'     # 或 'X'
    col_y = 'y'     # 或 'Y'
    col_z = 'VALUE' # 或 'GRID_CODE'

    # 檢查欄位是否存在
    if col_x in z_data.columns and col_y in z_data.columns and col_z in z_data.columns:
        
        # 1. 強制轉為數字
        z_data[col_x] = pd.to_numeric(z_data[col_x], errors='coerce')
        z_data[col_y] = pd.to_numeric(z_data[col_y], errors='coerce')
        z_data[col_z] = pd.to_numeric(z_data[col_z], errors='coerce')

        # 2. 移除髒資料並排序
        z_data = z_data.dropna()
        z_data = z_data.sort_values(by=[col_y, col_x])

        # 3. 轉換為矩陣 (Pivot)
        z_matrix = z_data.pivot(index=col_y, columns=col_x, values=col_z)
        
        # 4. 填補空洞 (優化視覺)
        # 改用「最小值」填補，而不是 0，這樣海底看起來比較自然
        min_val = z_matrix.min().min()
        z_matrix = z_matrix.fillna(min_val)

        # 5. 降低解析度 (Downsample) - 每 5 點取 1 點
        step = 5 
        z_matrix_small = z_matrix.iloc[::step, ::step]
        
        print(f"矩陣形狀: {z_matrix_small.shape}")

        if z_matrix_small.size == 0:
            raise ValueError("矩陣為空，可能是因為座標無法對齊")

        # 準備繪圖數據
        x_data = z_matrix_small.columns
        y_data = z_matrix_small.index
        z_data_matrix = z_matrix_small.values

        # 6. 建立圖表
        fig_3d = go.Figure(data=[
            go.Surface(
                x=x_data,
                y=y_data,
                z=z_data_matrix,
                colorscale="Earth", # 推薦 Earth 配色，比較像地形
                colorbar=dict(title="高程 (m)"),
                connectgaps=True    # 讓破洞連起來
            )
        ])

        # 7. 調整外觀與比例
        fig_3d.update_layout(
            title="澎湖地形 DEM 3D 模型",
            autosize=True,
            margin=dict(l=0, r=0, b=0, t=50),
            scene=dict(
                xaxis_title='經度',
                yaxis_title='緯度',
                zaxis_title='高程',
                # 📷 設定相機視角
                camera=dict(eye=dict(x=1.5, y=1.5, z=0.5)),
                # 📐 關鍵修正：壓縮 Z 軸比例
                aspectmode='manual',
                aspectratio=dict(x=1, y=1, z=0.1) # 改成 0.1 避免變成針山
            )
        )
        print("✅ 3D 圖表建立成功！")
        
    else:
        error_msg = f"❌ 欄位名稱錯誤！CSV 內的欄位是: {list(z_data.columns)}"
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
                "澎湖群島，坐擁台灣海峽最豐富的海洋生態，其壯麗的珊瑚礁不僅是海洋生物的家園，更是大自然賜予我們的珍貴資產。然而，在氣候變遷與人類活動的雙重影響下，這片美麗的水下森林正面臨前所未有的挑戰。"
                "本專案運用 Google Earth Engine 的開放資料，分類與分析 2015 年至 2025 年間的衛星影像，試圖從數據中拼湊出珊瑚礁棲地的消長。"
                "本網站展示了這些分析成果，透過互動式地圖與統計圖表，將複雜的遙測圖資轉化為直觀的數據資料，為海洋資源管理與決策提供科學依據。"
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
        
        with solara.Column(style={"width": "90%", "max-width": "1000px", "height": "700px"}):
            if fig_3d:
                solara.FigurePlotly(fig_3d)
                solara.Info("提示：滑鼠左鍵旋轉，右鍵平移，滾輪縮放。")
            else:
                solara.Error(error_msg if error_msg else "無法顯示 3D 圖表")