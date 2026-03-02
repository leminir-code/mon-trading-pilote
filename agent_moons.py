import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Terminal Moons Pro", layout="wide")
st.title("🏦 Terminal Expert : Stratégie Longue & Courte")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    # MODE DE TRADING
    st.subheader("🔄 Mode Opératoire")
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    st.subheader("⚠️ Risque & Calibration")
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 60, 30)

# --- BOUTONS D'ACTION ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper : Soldes ou Profit")

if btn_analyse or btn_anticipe:
    try:
        # Données Ichimoku (52j requis pour Senkou B)
        df = yf.download(ticker, period=f"{lookback+60}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS TECHNIQUES ---
            px_actuel = df_m['Close'].iloc[-1]
            
            # Ichimoku
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            sa = ((tenkan + kijun) / 2).shift(26)
            sb = ((df_m['High'].rolling(52).max() + df_m['Low'].rolling(52).min()) / 2).shift(26)
            chikou_vs_prix = df_m['Close'].shift(26).iloc[-1]

            # Fibonacci
            swing_high, swing_low = df['High'].tail(lookback).max(), df['Low'].tail(lookback).min()
            diff = swing_high - swing_low
            
            if mode == "ACHAT (Long)":
                fibo = {
                    "0.5": swing_high - (0.5 * diff),
                    "0.618": swing_high - (0.618 * diff),
                    "0.786": swing_high - (0.786 * diff),
                    "1.618": swing_high + (0.618 * diff)
                }
                stop_loss = min(sb.iloc[-1], fibo["0.786"])
                tp_objectif = fibo["1.618"]
            else: # MODE VENTE (Short)
                fibo = {
                    "0.5": swing_low + (0.5 * diff),
                    "0.618": swing_low + (0.618 * diff),
                    "0.786": swing_low + (0.786 * diff),
                    "1.618": swing_low - (0.618 * diff)
                }
                stop_loss = max(sb.iloc[-1], fibo["0.786"])
                tp_objectif = fibo["1.618"]

            # --- 1. AFFICHAGE PRIX LIVE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.divider()

            # --- 2. VERDICT INTELLIGENT (ACHAT vs VENTE) ---
            st.subheader(f"🤖 Verdict : Mode {mode}")
            
            if mode == "ACHAT (Long)":
                conds = [px_actuel > max(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] > sb.iloc[-1], 
                         tenkan.iloc[-1] > kijun.iloc[-1], px_actuel > chikou_vs_prix]
                score = sum(conds)
                in_zone = fibo["0.786"] <= px_actuel <= fibo["0.5"]
                
                if in_zone and score >= 3:
                    st.success(f"🔥 SIGNAL ACHAT : Confluence validée ({score}/4 Ichimoku).")
                elif px_actuel >= fibo["1.618"] * 0.98:
                    st.error("🚨 VENDRE : Objectif maximum atteint.")
                else: st.info("🔭 Observation : En attente de confluence haussière.")

            else: # ANALYSE VENTE
                conds = [px_actuel < min(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] < sb.iloc[-1], 
                         tenkan.iloc[-1] < kijun.iloc[-1], px_actuel < chikou_vs_prix]
                score = sum(conds)
                in_zone = fibo["0.5"] <= px_actuel <= fibo["0.786"]
                
                if in_zone and score >= 3:
                    st.error(f"📉 SIGNAL VENTE : Rebond de surchauffe validé ({score}/4 Ichimoku).")
                elif px_actuel <= fibo["1.618"] * 1.02:
                    st.success("🚨 COUVRIR : Objectif baissier maximum atteint.")
                else: st.info("🔭 Observation : En attente de confluence baissière.")

            # --- 3. CALCULATEUR RISQUE RÉEL ---
            dist_stop = abs(px_actuel - stop_loss)
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Risque dollar", f"-{(qte * dist_stop):.2f} $")
            c2.metric("Quantité suggérée", f"{qte}")
            c3.metric("Cible Profit", f"{tp_objectif:.2f} $")

            # --- 4. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line_color='rgba(0, 255, 0, 0.1)', name='SA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line_color='rgba(255, 0, 0, 0.1)', fill='tonexty', name='SB'), row=1, col=1)
            
            # Zone Action à gauche
            color_zone = "rgba(0, 255, 0, 0.1)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.1)"
            fig.add_hrect(y0=fibo["0.786"], y1=fibo["0.5"], fillcolor=color_zone, line_width=0, annotation_text="ZONE ACTION", annotation_position="top left", row=1, col=1)
            
            for k, v in fibo.items():
                fig.add_hline(y=v, line_color="rgba(255, 255, 255, 0.2)", annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right", row=1, col=1)

            # Volume
            vol_m = df_m['Volume'].rolling(20).mean()
            v_colors = ['#26a69a' if v > vol_m.iloc[-1] else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], marker_color=v_colors), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=750, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
