import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro", layout="wide")
st.title("🏦 Terminal Expert : Décisionnelle Assistée (Volume & Tendance)")

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
        df = yf.download(ticker, period=f"{lookback+10}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="5d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].tail(lookback).max(), df['Low'].tail(lookback).min()
            diff = swing_high - swing_low
            
            fibo = {
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "1.618": swing_high + (0.618 * diff)
            }

            # Tendance & Volume
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            vol_actuel = df_m['Volume'].iloc[-1]
            poussée_volume = vol_actuel > vol_moyen * 1.5

            # --- 1. AFFICHAGE PRIX LIVE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            # Badge de Tendance (Correction Point 1)
            tendance_txt = "HAUSSIER 🟢" if px_actuel > ma20 else "BAISSIER 🔴"
            st.markdown(f"<h3 style='text-align: center;'>Tendance : {tendance_txt} | Volume : {'🔥 Fort' if poussée_volume else '💤 Faible'}</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. LOGIQUE DE DÉCISION (Correction Point 2 & 3) ---
            if btn_anticipe:
                st.subheader("📉 Aide à la Décision")
                
                # Correction : Pas de "Soldes" si on coule sans volume acheteur
                if px_actuel <= fibo["0.5"] and px_actuel >= fibo["0.786"]:
                    if px_actuel < ma20 and not poussée_volume:
                        st.warning("⚠️ ZONE DE SOLDES ATTEINTE, mais la tendance est BAISSIÈRE sans volume acheteur. Attendez une bougie verte de confirmation.")
                    elif poussée_volume:
                        st.success("🛒 SOLDES VALIDÉES : Volume important détecté dans la zone. Opportunité d'achat.")
                    else:
                        st.info("🛒 Zone de soldes atteinte. Surveillez le retournement.")

                if px_actuel >= fibo["1.618"] * 0.98:
                    st.error("🚨 OBJECTIF MAX ATTEINT : Retracement Fibonacci 1.618 touché. Vendez.")

                # Calcul Quantité sur PRIX RÉEL (Correction Point 3)
                dist_stop_reel = abs(px_actuel - fibo["0.786"])
                qte = int((capital * risk_pc) / dist_stop_reel) if dist_stop_reel > 0 else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Risque Réel ($)", f"-{(qte * dist_stop_reel):.2f} $")
                c2.metric("Quantité (Prix Actuel)", f"{qte} titres")
                c3.metric("Objectif Vente", f"{fibo['1.618']:.2f} $")

            # --- 3. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zones
            fig.add_hrect(y0=fibo["0.786"], y1=fibo["0.5"], fillcolor="rgba(0, 255, 0, 0.1)", line_width=0, annotation_text="SOLDES", annotation_position="top left", row=1, col=1)
            
            # Lignes
            colors = {"0.5": "#00FF00", "0.618": "#00CED1", "0.786": "#FF4D4D", "1.618": "#FF00FF"}
            for k, v in fibo.items():
                fig.add_hline(y=v, line_color=colors[k], annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right", row=1, col=1)

            # Volume indicateur (Point 4)
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], marker_color=v_colors, name='Volume'), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
