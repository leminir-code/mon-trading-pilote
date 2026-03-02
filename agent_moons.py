import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Intelligence Pro", layout="wide")
st.title("🏦 Terminal Expert : Ichimoku & Anticipation Stratégique")

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
btn_anticipe = col_btn2.button("📈 Anticiper : Plan de Trade")

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
            chikou_vs_prix = df_m['Close'].shift(26).iloc[-1]

            # Fibonacci dynamique
            if mode == "ACHAT (Long)":
                fibo_levels = {
                    "0.5": swing_high - (0.5 * diff),
                    "0.618": swing_high - (0.618 * diff),
                    "0.786": swing_high - (0.786 * diff),
                    "1.618": swing_high + (0.618 * diff)
                }
                color_zone = "rgba(0, 255, 0, 0.12)"
            else:
                fibo_levels = {
                    "0.5": swing_low + (0.5 * diff),
                    "0.618": swing_low + (0.618 * diff),
                    "0.786": swing_low + (0.786 * diff),
                    "1.618": swing_low - (0.618 * diff)
                }
                color_zone = "rgba(255, 0, 0, 0.12)"

            # --- AFFICHAGE PRIX ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>Analyse basée sur un swing de <b>{lookback} jours</b></p>", unsafe_allow_html=True)
            st.divider()

            # --- LOGIQUE BOUTONS ---
            if btn_analyse:
                st.subheader(f"🚀 Diagnostic du Signal ({mode})")
                en_zone = min(fibo_levels["0.5"], fibo_levels["0.786"]) <= px_actuel <= max(fibo_levels["0.5"], fibo_levels["0.786"])
                
                # Check Ichimoku conditions (Long)
                conds = [px_actuel > max(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] > sb.iloc[-1], 
                         tenkan.iloc[-1] > kijun.iloc[-1], px_actuel > chikou_vs_prix]
                score = sum(conds) if mode == "ACHAT (Long)" else 4 - sum(conds)

                if en_zone:
                    st.success(f"🎯 PRIX EN ZONE D'INTERVENTION | Score Ichimoku : {score}/4")
                else:
                    st.info("🔭 Hors zone d'intervention. Observation recommandée.")

            elif btn_anticipe:
                st.subheader(f"📉 Plan d'Anticipation ({mode})")
                
                p_entree = fibo_levels["0.618"]
                p_target = fibo_levels["1.618"]
                dist_percent = ((p_entree / px_actuel) - 1) * 100
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("### 🎯 Consigne Stratégique")
                    if mode == "ACHAT (Long)":
                        if px_actuel > p_entree * 1.02:
                            st.warning(f"Attendre un repli de {abs(dist_percent):.2f}% vers {p_entree:.2f} $.")
                        elif px_actuel < fibo_levels["0.786"]:
                            st.error("Signal Invalidé : Le prix a enfoncé le stop psychologique.")
                        else:
                            st.success(f"ZONE D'ACHAT VALIDÉE : Visez l'extension à {p_target:.2f} $.")
                    else: # Mode Short
                        if px_actuel < p_entree * 0.98:
                            st.warning(f"Attendre un rebond de {abs(dist_percent):.2f}% vers {p_entree:.2f} $.")
                        else:
                            st.success(f"ZONE DE VENTE VALIDÉE : Visez l'extension à {p_target:.2f} $.")

                with col2:
                    st.write("### 💰 Niveaux de Trading")
                    st.metric("Entrée Idéale (0.618)", f"{p_entree:.2f} $")
                    st.metric("Objectif Final (1.618)", f"{p_target:.2f} $", delta=f"{((p_target/p_entree)-1)*100:.1f}%")

            # --- GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line=dict(color='rgba(0, 255, 0, 0.1)'), name='SA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo'), row=1, col=1)
            
            # Zone Action à Gauche
            fig.add_hrect(y0=fibo_levels["0.786"], y1=fibo_levels["0.5"], fillcolor=color_zone, line_width=0, 
                         annotation_text="ZONE ACTION", annotation_position="top left", row=1, col=1)
            
            # Prix Fibonacci à Droite
            for label, val in fibo_levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color="rgba(255,255,255,0.3)", 
                             annotation_text=f"{label} : {val:.2f}$", annotation_position="bottom right", row=1, col=1)

            # Volume
            v_colors = ['#26a69a' if v > df_m['Volume'].mean() else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], marker_color=v_colors), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
