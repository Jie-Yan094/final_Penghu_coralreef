import solara
import solara.lab

# ==========================================
# 1. 設定圖片網址基底
# ==========================================
# 這是你的 Hugging Face Space 檔案庫位置
base_url = "https://huggingface.co/spaces/jarita094/ThecoralreefsinPenghuwillthrive/resolve/main/"

# 定義圖片網址 (自動處理檔名中的空白)
img_healthy_2019 = f"{base_url}2019%20healthy%20coral.jpg"
img_dead_2021    = f"{base_url}2021%20dead%20coral.jpg"
img_clamp        = f"{base_url}Clamp%20starfish.jpg"
img_plant        = f"{base_url}Plant%20coral.png"
img_chart        = f"{base_url}Ocean%20debris%20chart.png"
img_net          = f"{base_url}fishing%20net.jpg"

# 尚未上傳的圖片暫時用海星代替，或者你可以換成其他的
img_placeholder  = "https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg"


# ==========================================
# 2. 資料設定
# ==========================================
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
    # 設定網頁主容器寬度與邊距
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "1200px", "margin": "0 auto"}):
        
        # --- 網站大標題 ---
        solara.Markdown("# 🌊 澎湖海域生態守護行動平台")
        solara.Markdown("### 守護核心：1.珊瑚復育與清星 | 2.海草床重建 | 3.海洋廢棄物(鬼網)清理")
        
        solara.v.Divider(style_="margin-bottom: 20px")

        # --- 1. 珊瑚區塊 (清除海星、復育) ---
        with solara.Card("🪸 珊瑚礁現況"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 🌊 影像對照")
                    
                    # 使用 Tabs 切換健康與死亡珊瑚
                    with solara.lab.Tabs():
                        for label, info in coral_data.items():
                            with solara.lab.Tab(label):
                                solara.Image(info["img"], width="100%")
                                solara.Markdown(f"**狀態：** {info['desc']}")
                    
                    solara.Markdown("澎湖海域珊瑚礁因氣候變遷、海洋酸化與人為干擾，近年來呈現衰退趨勢。")
                    solara.Markdown("目前主要以硬珊瑚為主，軟珊瑚比例較低。")

        # --- 2. 棘冠海星行動 ---
        with solara.Card("⭐ 行動一：⚔️ 棘冠海星(COTS)人工清除對策"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    
                    # A. 物理移除
                    solara.Markdown("##### **A. 物理移除 : 人工夾取**")
                    solara.Markdown("* 臺灣因成本考量、技術上限制，需由專業潛水員使用長夾將海星移入網袋帶回岸上處理。")
                    # 放照片：夾海星
                    solara.Image(img_clamp, width="100%")                
                    
                    # B. 生物化學
                    solara.Markdown("##### **B. 生物化學：醋酸注射法**")
                    solara.Markdown("* **優點：** 效率高、不需帶回岸上、不會引發海星斷肢再生。\n* **方法：** 使用注射槍將15%醋酸注入海星體內，其殘骸會自然分解回歸生態鏈。")
                    # 放照片：注射海星 (因為檔案列表沒看到注射的照片，暫時用夾海星或預設圖)
                    solara.Image(img_placeholder, width="100%")
                
                
        # --- 3. 珊瑚復育區塊 (行動二) ---
        with solara.Card("🪸 行動二：珊瑚復育 "):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 海洋花園植栽計畫")
                    solara.Markdown("""
                    澎湖縣政府與水產種苗場推動的珊瑚復育計畫，
                    在鎖港杭灣打造人工珊瑚礁生態系，利用軸孔珊瑚等進行無性繁殖與移植，形成水下「花園」。
                    """)
                    # 放照片：種珊瑚
                    solara.Image(img_plant, width="100%")

        # --- 4. 海洋廢棄物清理區塊 ---
        with solara.Card("🗑️ 行動三：海洋廢棄物清理 "):
            solara.Markdown(f"#### 海洋廢棄物統計資訊: [點此連結]({url_debris})")
            
            # 放照片：海洋垃圾圖表
            solara.Image(img_chart, width="100%")
            
            solara.Markdown("#### 海洋廢棄物治理計畫")
            solara.Markdown("除了因季風帶來的海洋垃圾問題之外，過度的捕撈，廢棄漁網會覆蓋珊瑚導致其死亡，並纏繞海龜等生物。")
            
            solara.Markdown("#### 相關報導：綠色和平清除廢網")
            # 放照片：漁網
            solara.Image(img_net, width="100%")
            solara.Markdown("* [綠色和平於澎湖海域清出約 400 公斤廢網](https://www.greenpeace.org/taiwan/press/32491/)")
        
        # --- 頁尾 ---
        solara.Markdown("<br>")
        solara.v.Divider()
        solara.Markdown("© 2025 澎湖珊瑚礁生態守護專案 | 數據來源：EE, iOcean, 澎湖縣政府", style="color:gray; text-align:center")