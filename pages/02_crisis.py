import solara
import leafmap.leafmap as leafmap
import pandas as pd
import plotly.graph_objects as go


# ==========================================
# 2. 頁面組件
# ==========================================
@solara.component
def Page():
    
    with solara.Column(align="center", style={"text-align": "center", "width": "100%"}):
        
        solara.Markdown("## 危害澎湖珊瑚礁之各項因子")
        with solara.Column(style={"max-width": "800px"}):
            solara.Markdown(
                """
                珊瑚礁生態系統面臨多重威脅，包括氣候變遷引發的海水溫度上升、海洋酸化、海水優樣化，以及人類活動如過度捕撈、污染和沿海開發等。這些因子不僅削弱了珊瑚的健康，還影響了整個生態系統的穩定性與生物多樣性。了解並減緩這些威脅對於保護澎湖珊瑚礁及其豐富的海洋生態至關重要。
                """
            )

        solara.Markdown("---")

        # --- 海溫區塊 ---
        solara.Markdown("## 1. 海溫分布變化")

        solara.Markdown("---")

        # --- 優養化區塊 ---
        solara.Markdown("## 2. 海洋優養化指標")

        solara.Markdown("---")

        # --- 珊瑚礁生態系崩壞區塊 ---
        solara.Markdown("## 3. 珊瑚礁生態系崩壞")
        solara.Markdown(
                """
                等一下我再來寫這裡
                """
            )
        solara.Markdown("---")

        # --- 人類活動影響 ---
        solara.Markdown("## 4. 人類活動影響-海洋垃圾")
        solara.Markdown(
                """
                這裡也等一下我再來寫
                """
            )
        solara.Markdown("---")
