import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Intelligence", layout="wide")
st.title("🏦 Terminal Expert : Confluence Ichimoku & Fibonacci")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 60, 30)

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper : Acheter ou Vendre")

if btn_analyse or btn_anticipe:
    try:
        # Données nécessaires pour Ichimoku (besoin de plus de recul pour Senkou B)
        df = yf.download(ticker, period=f"{lookback+52}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- 1. CALCULS ICHIMOKU ---
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            
            # Nuage (Kumo)
            sa = ((tenkan + kijun) / 2).shift(26)
            sb = ((df_m['High'].rolling(52).max() + df_m['Low'].rolling(52).min()) / 2).shift(26)
            
            # Chikou (Prix décalé de 26 en arrière pour la logique, ici on compare prix actuel vs prix -26)
            chikou_vs_prix = px_past_26 = df_m['Close'].shift(26).iloc[-1]

            # --- 2. CALCULS FIBONACCI ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].tail(lookback).max(), df['Low'].tail(lookback).min()
            diff = swing_high - swing_low
            
            fibo = {
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "1.618": swing_high + (0.618 * diff)
            }

            # --- 3. LOGIQUE DU PSEUDO-CODE (VÉRIFICATION DES 4 CONDITIONS) ---
            cond1 = px_actuel > max(sa.iloc[-1], sb.iloc[-1]) # Prix > Nuage
            cond2 = sa.iloc[-1] > sb.iloc[-1]                 # Nuage Futur (Actuel ici) Vert
            cond3 = tenkan.iloc[-1] > kijun.iloc[-1]         # Tenkan > Kijun (Croisement)
            cond4 = px_actuel > px_past_26                   # Chikou > Prix (Sortie)
            
            score_ichimoku = sum([cond1, cond2, cond3, cond4])
            en_zone_fibo = fibo["0.786"] <= px_actuel <= fibo["0.5"]

            # --- 4. AFFICHAGE ET VERDICT ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            st.subheader("🤖 Verdict Intelligence Artificielle (Ichimoku + Fibo)")
            
            if en_zone_fibo:
                if score_ichimoku == 4:
                    st.success(f"🔥 SIGNAL D'ACHAT FORT (4/4) : Confluence parfaite détectée.")
                else:
                    st.info(f"🟡 ZONE DE SOLDES : Fibonacci OK, mais Ichimoku incomplet ({score_ichimoku}/4 conditions).")
            elif px_actuel >= fibo["1.618"] * 0.98:
                st.error("🚨 VENTE : Extension Fibonacci 1.618 atteinte. Risque de retournement (Chikou à surveiller).")
            else:
                st.write("🔭 PHASE D'OBSERVATION : En attente d'un retracement ou d'un signal Ichimoku.")

            # --- 5. CALCULATEUR FINANCIER ---
            dist_stop = abs(px_actuel - min(sb.iloc[-1], swing_low)) # Stop sous le nuage ou swing low
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Risque (10%)", f"-{(qte * dist_stop):.2f} $")
            c2.metric("Quantité", f"{qte} titres")
            c3.metric("Take Profit (1:2)", f"{(px_actuel + (dist_stop * 2)):.2f} $")

            # --- 6. GRAPHIQUE ---
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'))
            
            # Nuage Ichimoku
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line_color='rgba(0, 255, 0, 0.1)', name='Senkou A'))
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line_color='rgba(255, 0, 0, 0.1)', fill='tonexty', name='Senkou B'))
            
            # Zone Fibo (à gauche)
            fig.add_hrect(y0=fibo["0.786"], y1=fibo["0.5"], fillcolor="rgba(255, 215, 0, 0.1)", line_width=0, annotation_text="ZONE D'INTERVENTION", annotation_position="top left")
            
            # Lignes de prix
            colors = {"0.5": "gray", "0.618": "#00CED1", "0.786": "#FF4D4D", "1.618": "#FF00FF"}
            for k, v in fibo.items():
                fig.add_hline(y=v, line_color=colors[k], annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
