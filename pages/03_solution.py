import solara
import solara.lab
import pathlib  # 用來讀取檔案路徑

# ==========================================
# 1. 圖片讀取小幫手 (讀取本機檔案)
# ==========================================
def get_image(filename):
    """
    這個函式會嘗試直接從伺服器硬碟讀取圖片。
    無論你的 Space 是公開還是私人，這招都有效。
    """
    # 1. 先找根目錄 (適用於 Hugging Face Space 環境)
    path = pathlib.Path(filename)
    
    # 2. 如果根目錄找不到，試試看上一層 (適用於本機開發環境)
    if not path.exists():
        path = pathlib.Path("..") / filename
        
    # 3. 如果找到了，回傳圖片的數據 (Bytes)
    if path.exists():
        return path.read_bytes()
    else:
        # 找不到就回傳一個預設的錯誤圖
        print(f"❌ 找不到圖片: {filename}")
        return "https://via.placeholder.com/300?text=Image+Not+Found"

# ==========================================
# 2. 設定資料 (直接讀入圖片數據)
# ==========================================
# 這裡我們不再存網址字串，而是直接存圖片的檔案內容
# 注意：這裡的檔名要跟你的截圖一模一樣 (包含空格)

img_healthy_2019 = get_image("2019 healthy coral.jpg")
img_dead_2021    = get_image("2021 dead coral.jpg")
img_clamp        = get_image("Clamp starfish.jpg")
img_plant        = get_image("Plant coral.png")
img_chart        = get_image("Ocean debris chart.png")
img_net          = get_image("fishing net.jpg")

# 備用圖 (這張還是用網址，因為它不在你的檔案列表裡)
img_placeholder  = "https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg"

coral_display_type = solara.reactive("硬珊瑚")

coral_data = {
    "2019 健康珊瑚礁": {
        "img": img_healthy_2019,
        "desc": "2019 健康珊瑚礁"
    },
    "2021 死亡珊瑚礁": {
        "img": img_dead_2021,
        "desc": "2021 死亡珊瑚礁(藻類附著)"
    }
}

url_debris = "https://iocean.oca.gov.tw/oca_oceanconservation/public/Marine_Litter_v2.aspx"

# ==========================================
# 3. 頁面組件
# ==========================================

@solara.component
def Page():
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "1200px", "margin": "0 auto"}):
        
        # --- 網站大標題 ---
        solara.Markdown("# 🌊 澎湖海域生態守護行動平台")
        solara.Markdown("### 守護核心：1.珊瑚復育與清星 | 2.海草床重建 | 3.海洋廢棄物(鬼網)清理")
        
        solara.v.Divider(style_="margin-bottom: 20px")

        # --- 1. 珊瑚區塊 ---
        with solara.Card("🪸 珊瑚礁現況"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 🌊 影像對照")
                    
                    with solara.lab.Tabs():
                        for label, info in coral_data.items():
                            with solara.lab.Tab(label):
                                # 這裡的 info["img"] 現在是圖片數據，Solara 會自動顯示
                                solara.Image(info["img"], width="100%")
                                solara.Markdown(f"**狀態：** {info['desc']}")
                    
                    solara.Markdown("澎湖海域珊瑚礁因氣候變遷、海洋酸化與人為干擾，近年來呈現衰退趨勢。")

        # --- 2. 棘冠海星行動 ---
        with solara.Card("⭐ 行動一：⚔️ 棘冠海星(COTS)人工清除對策"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    
                    solara.Markdown("##### **A. 物理移除 : 人工夾取**")
                    solara.Markdown("* 需由專業潛水員使用長夾將海星移入網袋帶回岸上處理。")
                    solara.Image(img_clamp, width="100%")                
                    
                    solara.Markdown("##### **B. 生物化學：醋酸注射法**")
                    solara.Markdown("* **優點：** 效率高、不需帶回岸上。\n* **方法：** 使用注射槍將15%醋酸注入海星體內。")
                    solara.Image(img_placeholder, width="100%")
                
        # --- 3. 珊瑚復育區塊 ---
        with solara.Card("🪸 行動二：珊瑚復育 "):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 海洋花園植栽計畫")
                    solara.Markdown("澎湖縣政府與水產種苗場推動的珊瑚復育計畫...")
                    solara.Image(img_plant, width="100%")

        # --- 4. 海洋廢棄物清理區塊 ---
        with solara.Card("🗑️ 行動三：海洋廢棄物清理 "):
            solara.Markdown(f"#### 海洋廢棄物統計資訊: [點此連結]({url_debris})")            
            solara.Image(img_chart, width="100%")
            solara.Markdown("#### 相關報導：綠色和平清除廢網")
            solara.Image(img_net, width="100%")
            solara.Markdown("* [綠色和平於澎湖海域清出約 400 公斤廢網](https://www.greenpeace.org/taiwan/press/32491/)")
        
        solara.Markdown("<br>")
        solara.v.Divider()
        solara.Markdown("© 2025 澎湖珊瑚礁生態守護專案", style="color:gray; text-align:center")