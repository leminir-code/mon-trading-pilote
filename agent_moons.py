import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Intelligence", layout="wide")
st.title("🏦 Terminal Expert : Analyse & Anticipation (Zones Actives)")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 60, 30)

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper : Soldes ou Profit")

if btn_analyse or btn_anticipe:
    try:
        df = yf.download(ticker, period=f"{lookback+60}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS COMMUNS ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].tail(lookback).max(), df['Low'].tail(lookback).min()
            diff = swing_high - swing_low
            
            # Ichimoku
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            sa = ((tenkan + kijun) / 2).shift(26)
            sb = ((df_m['High'].rolling(52).max() + df_m['Low'].rolling(52).min()) / 2).shift(26)
            chikou_vs_prix = df_m['Close'].shift(26).iloc[-1]

            # Fibonacci & Zones
            if mode == "ACHAT (Long)":
                f_05, f_0618, f_0786 = swing_high - (0.5 * diff), swing_high - (0.618 * diff), swing_high - (0.786 * diff)
                f_target = swing_high + (0.618 * diff)
                color_zone = "rgba(0, 255, 0, 0.12)" # Vert pour achat
            else:
                f_05, f_0618, f_0786 = swing_low + (0.5 * diff), swing_low + (0.618 * diff), swing_low + (0.786 * diff)
                f_target = swing_low - (0.618 * diff)
                color_zone = "rgba(255, 0, 0, 0.12)" # Rouge pour vente

            # --- AFFICHAGE PRIX ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.divider()

            # --- LOGIQUE BOUTONS ---
            if btn_analyse:
                st.subheader("🚀 Diagnostic du Signal")
                en_zone = min(f_05, f_0786) <= px_actuel <= max(f_05, f_0786)
                if en_zone: st.success("🎯 PRIX EN ZONE D'INTERVENTION")
                else: st.info("🔭 Hors zone d'intervention")

            elif btn_anticipe:
                st.subheader("📉 Plan d'Anticipation")
                st.metric("Objectif Max", f"{f_target:.2f} $")

            # --- GRAPHIQUE AVEC ZONE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # RÉINTÉGRATION DE LA ZONE (À gauche)
            fig.add_hrect(
                y0=f_0786, y1=f_05, 
                fillcolor=color_zone, line_width=0, 
                annotation_text="ZONE D'INTERVENTION", annotation_position="top left", 
                row=1, col=1
            )
            
            # Lignes Fibonacci (À droite)
            levels = {"0.5": f_05, "0.618": f_0618, "0.786": f_0786, "1.618": f_target}
            for label, val in levels.items():
                fig.add_hline(y=val, line_color="rgba(255,255,255,0.2)", annotation_text=f"{label} ({val:.2f}$)", annotation_position="bottom right", row=1, col=1)

            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
