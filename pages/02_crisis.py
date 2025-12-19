import solara
import leafmap
import ee
import os
import json
from google.oauth2.service_account import Credentials

# 定義一個全域變數來儲存錯誤訊息，讓它顯示在網頁上
error_message = solara.reactive("")
success_message = solara.reactive("")

# ==========================================
# 0. GEE 驗證與初始化 (診斷模式)
# ==========================================
def initialize_gee():
    try:
        key_content = os.environ.get('EARTHENGINE_TOKEN')
        if not key_content:
            return "❌ 錯誤：找不到 EARTHENGINE_TOKEN，請檢查 Hugging Face Secrets。"

        service_account_info = json.loads(key_content)
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/earthengine']
        )
        # 重新初始化
        ee.Initialize(credentials=creds, project='ee-s1243037-0')
        return "✅ GEE 驗證成功！"
    except Exception as e:
        return f"❌ GEE 初始化失敗: {str(e)}"

# 執行初始化並儲存結果
init_result = initialize_gee()

# ==========================================
# 1. 變數定義
# ==========================================
selected_year = solara.reactive(2023) # 先預設一個絕對有資料的年份

# ==========================================
# 2. 地圖生產函數 (含錯誤回報)
# ==========================================
def get_diagnostic_map(year_val):
    m = leafmap.Map(center=[23.5, 119.5], zoom=12)
    m.add_basemap("HYBRID")

    # --- 測試 1: 簡單地形圖 (確認帳號權限) ---
    try:
        dem = ee.Image('USGS/SRTMGL1_003')
        vis = {'min': 0, 'max': 100, 'palette': ['black', 'white']}
        m.add_ee_layer(dem, vis, "測試圖層 (地形圖)")
        success_message.set("✅ 測試圖層載入成功！帳號權限正常。")
    except Exception as e:
        error_message.set(f"❌ 測試圖層失敗 (帳號權限有問題): {str(e)}")
        return m # 如果連這個都失敗，下面就不用跑了

    # --- 測試 2: Sentinel-2 衛星圖 (確認資料讀取) ---
    try:
        roi = ee.Geometry.Rectangle([119.3, 23.1, 119.8, 23.8])
        start_date = f'{year_val}-01-01'
        end_date = f'{year_val}-12-31'
        
        # 為了除錯，我們先拿掉雲量過濾，看是不是真的沒照片
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(roi)
                      .filterDate(start_date, end_date)
                      # .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) # 先註解掉
                      .median())

        ndci = collection.normalizedDifference(['B5', 'B4']).rename('NDCI')
        
        # 檢查該區域是否真的有資料 (這一步會稍微慢一點)
        # 如果這裡報錯，代表該年份完全沒照片
        _ = collection.get('system:id').getInfo() 

        vis_params = {'min': -0.1, 'max': 0.5, 'palette': ['blue', 'white', 'red']}
        m.add_ee_layer(ndci.clip(roi), vis_params, f"{year_val} NDCI")
        
    except Exception as e:
        # 這裡的錯誤通常是因為運算超時或沒資料，雖然報錯但地圖還是會出來
        # 我們把具體原因印出來
        current_err = error_message.value
        error_message.set(f"{current_err} \n⚠️ 衛星圖層載入警告: {str(e)}")

    return m

# ==========================================
# 3. 頁面組件
# ==========================================
@solara.component
def Page():
    with solara.Column(align="center", style={"width": "100%"}):
        
        solara.Markdown("## GEE 連線診斷模式")
        
        # 顯示初始化結果
        if "❌" in init_result:
            solara.Error(init_result)
        else:
            solara.Success(init_result)

        # 顯示地圖載入的錯誤訊息 (如果有的話)
        if error_message.value:
            solara.Error(f"地圖錯誤: {error_message.value}")
        
        if success_message.value:
            solara.Success(success_message.value)

        # 滑桿
        solara.SliderInt(label="選擇年份", value=selected_year, min=2016, max=2024)
        
        # 顯示地圖
        m = get_diagnostic_map(selected_year.value)
        m.element(height="600px", width="100%")