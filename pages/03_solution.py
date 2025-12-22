import solara
import solara.lab

# ... (GEE 驗證部分保持不變) ...

# 1. 核心資料
coral_display_type = solara.reactive("硬珊瑚")

coral_data = {
    "2019 健康珊瑚礁": {
        "img": "https://huggingface.co/jarita094/starfish-assets/resolve/main/before_cots.jpg",
        "desc": "2019 健康珊瑚礁"
    },
    "2021 死亡珊瑚礁": {
        "img": "https://huggingface.co/jarita094/starfish-assets/resolve/main/after_restoration.jpg",
        "desc": "2021 死亡珊瑚礁(藻類附著)"
    }
}

url = "https://iocean.oca.gov.tw/oca_oceanconservation/public/Marine_Litter_v2.aspx"

# 2. 頁面組件定義
@solara.component
def Page():
    # 設定網頁主容器
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "1200px", "margin": "0 auto"}):
        
        # --- 網站大標題 ---
        solara.Markdown("# 🌊 澎湖海域生態守護行動平台")
        solara.Markdown("### 守護核心：1.珊瑚復育與清星 | 2.海草床重建 | 3.海洋廢棄物(鬼網)清理")
        solara.v.Divider(style_="margin-bottom: 20px") 

        # --- 區塊 1: 珊瑚礁現況 ---
        with solara.Card("🪸 珊瑚礁現況"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 🌊 影像對照")
                    # 修正 Tabs 縮進
                    with solara.lab.Tabs():
                        for label, info in coral_data.items():
                            with solara.lab.Tab(label):
                                solara.Image(info["img"], width="100%", style={"border-radius": "10px"})
                                solara.Markdown(f"**狀態：** {info['desc']}")
                    
                    solara.Markdown("澎湖海域珊瑚礁因氣候變遷、海洋酸化與人為干擾，近年來呈現衰退趨勢。目前主要以硬珊瑚為主。")

        # --- 區塊 2: 棘冠海星對策 ---
        with solara.Card("⭐ 行動一：⚔️ 棘冠海星(COTS)人工清除對策", style={"margin-top": "20px"}):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("##### **A. 物理移除：人工夾取**")
                    solara.Markdown("* 臺灣需由專業潛水員使用長夾將海星移入網袋，效率低且人力消耗大。")
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/manual_removal.jpg", width="100%", style={"border-radius": "10px"})
                
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("##### **B. 生物化學：醋酸注射法**")
                    solara.Markdown("* **優點：** 不會引發斷肢再生，殘骸自然分解。\n* **方法：** 使用注射槍將 15% 醋酸注入體內。")
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/chemical_removal.jpg", width="100%", style={"border-radius": "10px"})

        # --- 區塊 3: 珊瑚復育 ---
        with solara.Card("🌱 行動二：珊瑚復育計畫", style={"margin-top": "20px"}):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 海洋花園植栽計畫")
                    solara.Markdown("澎湖縣政府與水產種苗場推動，在鎖港杭灣利用軸孔珊瑚進行無性繁殖與移植。")
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/coral_planting.jpg", width="100%", style={"border-radius": "10px"})

        # --- 區塊 4: 海洋廢棄物 ---
        with solara.Card("🗑️ 行動三：海洋廢棄物清理", style={"margin-top": "20px"}):
            solara.Markdown(f"#### [海洋廢棄物統計資訊網]({url})")
            solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/coral_planting.jpg", width="100%", style={"border-radius": "10px"})
            solara.Markdown("#### 海洋廢棄物治理計畫")
            solara.Markdown("過度捕撈與廢棄漁網會覆蓋珊瑚導致其死亡，並纏繞海龜等生物。")
            solara.Markdown("🔗 **相關報導：**")
            solara.Markdown("[綠色和平於澎湖海域清出 400 公斤廢網](https://www.greenpeace.org/taiwan/press/32491/%E7%B6%A0%E8%89%B2%E5%92%8C%E5%B9%B3%E6%96%BC%E6%BE%8E%E6%B9%96%E6%B5%B7%E5%9F%9F%E6%B8%85%E5%87%BA%E7%B4%84-400-%E5%85%AC%E6%96%A4%E5%BB%A2%E7%B6%B2-%E4%BF%9D%E8%AD%B7%E5%8D%80%E6%B5%B7%E6%B4%8B/)")

        # --- 頁尾 ---
        solara.Markdown("<br>")
        solara.v.Divider()
        solara.Markdown("© 2025 澎湖珊瑚礁生態守護專案 | 數據來源：EE, iOcean, 澎湖縣政府", style="color:gray; text-align:center")

# 啟動 Page
Page()