import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Intelligence", layout="wide")
st.title("🏦 Terminal Expert : Ichimoku & Fibonacci (Affichage Optimisé)")

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
        # Données
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

            # Volume
            vol_actuel = df_m['Volume'].iloc[-1]
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            ratio_vol = vol_actuel / vol_moyen

            # Fibonacci dynamique selon le mode
            if mode == "ACHAT (Long)":
                f_05, f_0618, f_0786 = swing_high - (0.5 * diff), swing_high - (0.618 * diff), swing_high - (0.786 * diff)
                f_target = swing_high + (0.618 * diff)
                color_zone = "rgba(0, 255, 0, 0.12)"
            else:
                f_05, f_0618, f_0786 = swing_low + (0.5 * diff), swing_low + (0.618 * diff), swing_low + (0.786 * diff)
                f_target = swing_low - (0.618 * diff)
                color_zone = "rgba(255, 0, 0, 0.12)"

            # --- AFFICHAGE PRIX ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>Swing : <b>{lookback} jours</b> | Volume : <b>{ratio_vol:.2f}x</b></p>", unsafe_allow_html=True)
            st.divider()

            # --- LOGIQUE BOUTONS ---
            if btn_analyse:
                st.subheader("🚀 Diagnostic du Signal")
                en_zone = min(f_05, f_0786) <= px_actuel <= max(f_05, f_0786)
                if en_zone: st.success("🎯 PRIX EN ZONE D'INTERVENTION")
                else: st.info("🔭 Hors zone d'intervention.")

            elif btn_anticipe:
                st.subheader("📉 Plan d'Anticipation")
                st.metric("Objectif Fibonacci 1.618", f"{f_target:.2f} $")

            # --- GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # Prix & Ichimoku
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Senkou A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo'), row=1, col=1)
            
            # Lignes Tenkan/Kijun (Optionnel, désactivé par défaut pour clarté)
            # fig.add_trace(go.Scatter(x=df_m.index, y=tenkan, line=dict(color='#00FFFF', width=1), name='Tenkan'), row=1, col=1)
            # fig.add_trace(go.Scatter(x=df_m.index, y=kijun, line=dict(color='#FFFF00', width=1), name='Kijun'), row=1, col=1)

            # ZONE D'INTERVENTION - ANNOTATION DÉPLACÉE À GAUCHE
            fig.add_hrect(
                y0=f_0786, y1=f_05, 
                fillcolor=color_zone, line_width=0, 
                annotation_text="ZONE ACTION", 
                annotation_position="top left", # <-- CORRECTION : Déplacement à gauche
                row=1, col=1
            )
            
            # LIGNES DE PRIX À DROITE (Pour éviter les superpositions)
            levels = {"0.5": f_05, "0.618": f_0618, "0.786": f_0786, "OBJ 1.618": f_target}
            for label, val in levels.items():
                fig.add_hline(
                    y=val, 
                    line_dash="dot", 
                    line_color="rgba(255,255,255,0.4)", 
                    annotation_text=f"{label} : {val:.2f}$", 
                    annotation_position="bottom right", # <-- PRIX À DROITE
                    row=1, col=1
                )

            # Volume
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], marker_color=v_colors), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
