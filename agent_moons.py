import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Terminal Moons Intelligence", layout="wide")
st.title("🏦 Terminal Expert : Analyse & Anticipation (Ichimoku-Fibo)")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 60, 30)

# --- STRUCTURE DES BOUTONS ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper : Soldes ou Profit")

if btn_analyse or btn_anticipe:
    try:
        # Récupération des données (60j pour Senkou B)
        df = yf.download(ticker, period=f"{lookback+60}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS COMMUNS ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].tail(lookback).max(), df['Low'].tail(lookback).min()
            diff = swing_high - swing_low
            
            # Ichimoku Components
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            sa = ((tenkan + kijun) / 2).shift(26)
            sb = ((df_m['High'].rolling(52).max() + df_m['Low'].rolling(52).min()) / 2).shift(26)
            chikou_vs_prix = df_m['Close'].shift(26).iloc[-1]

            # --- AFFICHAGE PRIX LIVE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.divider()

            # --- 🚀 CAS 1 : ANALYSER LE SIGNAL ACTUEL ---
            if btn_analyse:
                st.subheader("🚀 Diagnostic du Signal Immédiat")
                
                # Check des 4 conditions Ichimoku (Long ou Short)
                if mode == "ACHAT (Long)":
                    conds = [px_actuel > max(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] > sb.iloc[-1], 
                             tenkan.iloc[-1] > kijun.iloc[-1], px_actuel > chikou_vs_prix]
                    score = sum(conds)
                    fibo_low, fibo_high = swing_high - (0.786 * diff), swing_high - (0.5 * diff)
                    en_zone = fibo_low <= px_actuel <= fibo_high
                else:
                    conds = [px_actuel < min(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] < sb.iloc[-1], 
                             tenkan.iloc[-1] < kijun.iloc[-1], px_actuel < chikou_vs_prix]
                    score = sum(conds)
                    fibo_low, fibo_high = swing_low + (0.5 * diff), swing_low + (0.786 * diff)
                    en_zone = fibo_low <= px_actuel <= fibo_high

                # Verdict Analyse
                if en_zone and score == 4:
                    st.success(f"🔥 SIGNAL {mode} FORT : Confluence parfaite détectée ({score}/4).")
                elif en_zone:
                    st.info(f"🟡 ZONE DE DÉCISION : Fibonacci OK, mais Ichimoku incomplet ({score}/4).")
                else:
                    st.warning("🔭 HORS ZONE : Le prix n'est pas dans une zone de rebond Fibonacci.")

            # --- 📉 CAS 2 : ANTICIPER LES SOLDES OU PROFIT ---
            elif btn_anticipe:
                st.subheader("📉 Plan d'Anticipation (Stratégie Future)")
                
                if mode == "ACHAT (Long)":
                    p_soldes = swing_high - (0.618 * diff)
                    p_profit_max = swing_high + (0.618 * diff)
                    p_stop = swing_high - (0.786 * diff)
                    
                    if px_actuel >= p_profit_max * 0.98:
                        st.error(f"🚨 VENDRE : Objectif Fibonacci 1.618 atteint ({p_profit_max:.2f} $).")
                    elif px_actuel <= p_soldes * 1.02:
                        st.success(f"🛒 C'EST LES SOLDES : Zone d'achat identifiée vers {p_soldes:.2f} $.")
                    else:
                        st.info(f"💡 Anticipation : Attente d'un retour aux soldes ({p_soldes:.2f} $).")
                else: # Mode VENTE
                    p_soldes = swing_low + (0.618 * diff)
                    p_profit_max = swing_low - (0.618 * diff)
                    p_stop = swing_low + (0.786 * diff)
                    
                    if px_actuel <= p_profit_max * 1.02:
                        st.success(f"🚨 COUVRIR : Profit maximum atteint ({p_profit_max:.2f} $).")
                    elif px_actuel >= p_soldes * 0.98:
                        st.error(f"📉 OPPORTUNITÉ VENTE : Zone de surchauffe vers {p_soldes:.2f} $.")

                # Calcul Risque sur Anticipation
                dist_stop = abs(px_actuel - p_stop)
                qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
                c1, c2, c3 = st.columns(3)
                c1.metric("Prix Cible", f"{p_soldes:.2f} $")
                c2.metric("Quantité", f"{qte}")
                c3.metric("Profit Visé", f"{p_profit_max:.2f} $")

            # --- GRAPHIQUE COMMUN ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line_color='rgba(0, 255, 0, 0.1)', name='SA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line_color='rgba(255, 0, 0, 0.1)', fill='tonexty', name='SB'), row=1, col=1)
            
            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
