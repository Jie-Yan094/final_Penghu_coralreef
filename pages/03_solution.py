import solara
import solara.lab
import geemap.foliumap as geemap
import ee
import os
import json
import tempfile
import pandas as pd
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# ... (GEE 驗證與初始化部分保持不變) ...

# ==========================================
# 1. 核心資料與狀態設定
# ==========================================
coral_display_type = solara.reactive("硬珊瑚")


# ==========================================
# 2. 頁面組件:珊瑚
# ==========================================
# 這裡要放照片-珊瑚礁
coral_data = {
    "2019 健康珊瑚礁": {
        "img": "https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg",
        "desc": "2019 健康珊瑚礁"
    },
    "2021 死亡珊瑚礁": {
        "img": "https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg",
        "desc": "2021 死亡珊瑚礁(藻類附著)"
    }
}

# ==========================================
# 3. 頁面組件:垃圾
# ==========================================
url = "https://iocean.oca.gov.tw/oca_oceanconservation/public/Marine_Litter_v2.aspx"

# ==========================================
# 4. 頁面組件
# ==========================================

@solara.component
def Page():
    # 設定網頁主容器寬度與邊距
    with solara.Column(style={"width": "100%", "padding": "20px", "max-width": "1200px", "margin": "0 auto"}):
        
        # --- 網站大標題 ---
        solara.Markdown("# 🌊 澎湖海域生態守護行動平台")
        solara.Markdown("### 守護核心：1.珊瑚復育與清星 | 2.海草床重建 | 3.海洋廢棄物(鬼網)清理")
        
        # [修正] 使用 solara.v.Divider() 代替 solara.Divider()
        solara.v.Divider(style_="margin-bottom: 20px")

        # --- 1. 珊瑚區塊 (清除海星、復育) ---
        with solara.Card("🪸 珊瑚礁現況"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 🌊 影像對照")
                    
                    # 使用迴圈自動生成分頁，減少重複代碼
                    with solara.lab.Tabs():
                        for label, info in coral_data.items():
                            with solara.lab.Tab(label):
                                solara.Image(info["img"], width="100%", style={"border-radius": "10px"})
                                solara.Markdown(f"**狀態：** {info['desc']}")
                    
                    solara.Markdown("澎湖海域珊瑚礁因氣候變遷、海洋酸化與人為干擾，近年來呈現衰退趨勢。")
                    solara.Markdown("目前主要以硬珊瑚為主，軟珊瑚比例較低。")

        # --- 2. 棘冠海星行動 ---
        with solara.Card("⭐ 行動一：⚔️ 棘冠海星(COTS)人工清除對策"):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("##### **A. 物理移除 : 人工夾取**")
                    solara.Markdown("* 臺灣因成本考量、技術上限制，需由專業潛水員使用長夾將海星移入網袋帶回岸上處理，但效率低且人力消耗大。")
                    # 這裡要放照片-夾海星
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%", style={"border-radius": "10px"})
                    
                    solara.Markdown("##### **B. 生物化學：醋酸注射法**")
                    solara.Markdown("* **優點：** 效率高、不需帶回岸上、不會引發海星斷肢再生。\n* **方法：** 使用注射槍將15%醋酸注入海星體內，其殘骸會自然分解回歸生態鏈。")
                    # 這裡要放照片-注射海星
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%", style={"border-radius": "10px"})
                
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 🌿 珊瑚復育技術")
                    solara.Markdown("* **珊瑚種植：** 採集天然殘枝，於陸域養殖中心培育後，再利用不鏽鋼架或生態磚進行海域移植復育。")

        # --- 3. 珊瑚復育區塊 (行動二) ---
        with solara.Card("🪸 行動二：珊瑚復育 "):
            with solara.Row(gap="20px", style={"flex-wrap": "wrap"}):
                with solara.Column(style={"flex": "1", "min-width": "450px"}):
                    solara.Markdown("#### 海洋花園植栽計畫")
                    solara.Markdown("""
                    澎湖縣政府與水產種苗場推動的珊瑚復育計畫，
                    在鎖港杭灣打造人工珊瑚礁生態系，利用軸孔珊瑚等進行無性繁殖與移植，形成水下「花園」，復育豐富的海洋生物，同時結合海洋教育和在地潛水業者，發展生態旅遊。
                    """)
                    # 這裡要放照片-種珊瑚
                    solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%", style={"border-radius": "10px"})

        # --- 4. 海洋廢棄物清理區塊 ---
        with solara.Card("🗑️ 行動三：海洋廢棄物清理 "):
            solara.Markdown(f"#### 海洋廢棄物統計資訊: [點此連結]({url})")
            # 這裡要放照片-海洋垃圾圖表_來不及做
            solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%", style={"border-radius": "10px"})
            
            solara.Markdown("#### 海洋廢棄物治理計畫")
            solara.Markdown("除了因季風帶來的海洋垃圾問題之外，過度的捕撈，廢棄漁網會覆蓋珊瑚導致其死亡，並纏繞海龜等生物。")
            solara.Markdown("#### 相關報導")
            # 這裡要放照片
            solara.Image("https://huggingface.co/jarita094/starfish-assets/resolve/main/starfish.jpg", width="100%", style={"border-radius": "10px"})
            solara.Markdown("* [綠色和平於澎湖海域清出約 400 公斤廢網](https://www.greenpeace.org/taiwan/press/32491/%E7%B6%A0%E8%89%B2%E5%92%8C%E5%B9%B3%E6%96%BC%E6%BE%8E%E6%B9%96%E6%B5%B7%E5%9F%9F%E6%B8%85%E5%87%BA%E7%B4%84-400-%E5%85%AC%E6%96%A4%E5%BB%A2%E7%B6%B2-%E4%BF%9D%E8%AD%B7%E5%8D%80%E6%B5%B7%E6%B4%8B/)")
        
        # --- 頁尾 ---
        solara.Markdown("<br>")
        solara.v.Divider()
        solara.Markdown("© 2025 澎湖珊瑚礁生態守護專案 | 數據來源：EE, iOcean, 澎湖縣政府", style="color:gray; text-align:center")

# ==========================================
# 5. 執行
# ==========================================
# Page() # 如果在 solara app 中，這行通常不需要，solara 會自動尋找 Page 組件