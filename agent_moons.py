import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Ichimoku-Fibo Expert", layout="wide")
st.title("🏦 Terminal Expert : Stratégie Combinée (TradingView Style)")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="AAPL").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 5.0, 1.0) / 100

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes / Hausse")

if btn_analyse or btn_anticipe:
    try:
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ICHIMOKU (15m pour exécution) ---
            high_9 = df_m['High'].rolling(9).max()
            low_9 = df_m['Low'].rolling(9).min()
            tenkan = (high_9 + low_9) / 2
            
            high_26 = df_m['High'].rolling(26).max()
            low_26 = df_m['Low'].rolling(26).min()
            kijun = (high_26 + low_26) / 2
            
            senkou_a = ((tenkan + kijun) / 2).shift(26)
            high_52 = df_m['High'].rolling(52).max()
            low_52 = df_m['Low'].rolling(52).min()
            senkou_b = ((high_52 + low_52) / 2).shift(26)

            # --- CALCULS FIBONACCI ---
            swing_high, swing_low = df['High'].tail(30).max(), df['Low'].tail(30).min()
            diff = swing_high - swing_low
            levels = {
                "Entrée 0.618": swing_high - (0.618 * diff),
                "Stop 0.786": swing_high - (0.786 * diff),
                "Objectif 1.272": swing_high + (0.272 * diff)
            }
            px_actuel = df_m['Close'].iloc[-1]

            # --- 1. PRIX ACTUEL ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.divider()

            # --- 2. RÉCAPITULATIF STRATÉGIQUE ---
            st.write("### 📝 Plan de Trade (Règles TradingView)")
            c1, c2, c3 = st.columns(3)
            c1.metric("Achat (61.8%)", f"{levels['Entrée 0.618']:.2f} $")
            c2.metric("Sortie (127.2%)", f"{levels['Objectif 1.272']:.2f} $")
            c3.metric("Stop Loss (78.6%)", f"{levels['Stop 0.786']:.2f} $")

            # --- 3. CALCULATEUR RISQUE ---
            dist_stop = abs(levels['Entrée 0.618'] - levels['Stop 0.786'])
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            gain_pot = qte * abs(levels['Objectif 1.272'] - levels['Entrée 0.618'])
            
            cg1, cg2, cg3 = st.columns(3)
            cg1.metric("🔴 Risque Total", f"-{(qte * dist_stop):.2f} $")
            cg2.metric("🟢 Gain Espéré", f"+{gain_pot:.2f} $")
            cg3.metric("📦 Quantité", f"{qte} titres")

            # --- 4. VALIDATION DU SIGNAL ---
            cond_cloud = px_actuel > max(senkou_a.iloc[-1], senkou_b.iloc[-1])
            cond_tk = tenkan.iloc[-1] > kijun.iloc[-1]
            cond_fibo = px_actuel <= (levels['Entrée 0.618'] * 1.01) # Proche du 61.8%

            st.write("---")
            if cond_cloud and cond_tk and cond_fibo:
                st.success("🔥 SIGNAL D'ACHAT VALIDÉ : Tendance haussière + Repli sur 61.8% terminé.")
            else:
                st.info("⌛ En attente de convergence : Le prix doit être au-dessus du nuage et toucher le niveau 61.8%.")

            # --- 5. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku Cloud
            fig.add_trace(go.Scatter(x=df_m.index, y=senkou_a, line_color='rgba(0, 255, 0, 0.2)', name='Cloud A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=senkou_b, line_color='rgba(255, 0, 0, 0.2)', fill='tonexty', name='Cloud B'), row=1, col=1)

            # Zone de Soldes Pastel (61.8%)
            fig.add_hrect(y0=levels["Stop 0.786"], y1=levels["Entrée 0.618"], fillcolor="rgba(255, 215, 0, 0.15)", line_width=0, annotation_text="ZONE D'ENTRÉE", annotation_position="top left", row=1, col=1)
            
            # Lignes de prix
            colors = {"Entrée 0.618": "#00ff00", "Stop 0.786": "#ff4d4d", "Objectif 1.272": "#ff00ff"}
            for label, val in levels.items():
                fig.add_hline(y=val, line_color=colors[label], annotation_text=f"{label} ({val:.2f}$)", annotation_position="bottom right", row=1, col=1)

            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
