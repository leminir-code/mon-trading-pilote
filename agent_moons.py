import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Stratégique", layout="wide")
st.title("🏦 Terminal Expert : Stratégies Fibonacci & Ichimoku")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)

def get_ichimoku_score(data, mode_trade):
    if len(data) < 52: return 0
    px = data['Close'].iloc[-1]
    h9, l9 = data['High'].rolling(9).max(), data['Low'].rolling(9).min()
    tenkan = (h9 + l9) / 2
    h26, l26 = data['High'].rolling(26).max(), data['Low'].rolling(26).min()
    kijun = (h26 + l26) / 2
    sa = ((tenkan + kijun) / 2).shift(26)
    sb = ((data['High'].rolling(52).max() + data['Low'].rolling(52).min()) / 2).shift(26)
    chikou_lib = px > data['Close'].shift(26).iloc[-1] if mode_trade == "ACHAT (Long)" else px < data['Close'].shift(26).iloc[-1]
    
    if mode_trade == "ACHAT (Long)":
        conds = [px > max(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] > sb.iloc[-1], tenkan.iloc[-1] > kijun.iloc[-1], chikou_lib]
    else:
        conds = [px < min(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] < sb.iloc[-1], tenkan.iloc[-1] < kijun.iloc[-1], chikou_lib]
    return sum(conds)

if st.button("🚀 Lancer l'Analyse Stratégique"):
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            # --- 1. DÉTECTION DU SWING & CALCUL FIBO ---
            df_recent = df_d.tail(lookback)
            swing_high = df_recent['High'].max()
            swing_low = df_recent['Low'].min()
            diff = swing_high - swing_low
            px_actuel = df_15['Close'].iloc[-1]

            # Définition des niveaux selon le mode
            if mode == "ACHAT (Long)":
                p_entree = swing_high - (0.618 * diff)  # Entrée aux soldes
                p_stop = swing_high - (0.786 * diff)
                p_sortie = swing_high + (0.618 * diff) # Objectif Bull
            else:
                p_entree = swing_low + (0.618 * diff)   # Entrée au rebond
                p_stop = swing_high + (0.786 * diff)
                p_sortie = swing_low - (0.618 * diff)  # Objectif Bear

            # --- 2. DIAGNOSTIC MARCHÉ (BULL VS BEAR) ---
            score_d = get_ichimoku_score(df_d, mode)
            market_type = "BULL 🟢" if score_d >= 3 else "BEAR 🔴"

            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $ ({market_type})</h1>", unsafe_allow_html=True)
            
            # --- 3. RECOMMANDATIONS STRATÉGIQUES ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Recommandation d'Entrée")
                dist_entree = ((p_entree / px_actuel) - 1) * 100
                if market_type == "BEAR 🔴":
                    st.info(f"Marché baissier : N'achetez pas au prix actuel. Attendez la zone de soldes Fibo à **{p_entree:.2f} $** (soit un repli de {abs(dist_entree):.2f}%).")
                else:
                    if px_actuel <= p_entree * 1.02:
                        st.success(f"Opportunité Bull : Le prix est idéal pour entrer. Prix suggéré : **{p_entree:.2f} $**.")
                    else:
                        st.warning(f"Tendance Bull confirmée, mais prix trop haut. Attendez un retour à **{p_entree:.2f} $**.")

            with col2:
                st.subheader("💰 Gestion de Sortie")
                if market_type == "BULL 🟢":
                    st.success(f"Objectif de vente conseillé (Extension 1.618) : **{p_sortie:.2f} $**.")
                else:
                    st.error(f"Marché Bear : Si vous entrez à {p_entree:.2f} $, visez un rachat rapide ou un profit à **{p_sortie:.2f} $**.")

            # --- 4. GRAPHIQUE ---
            df_plot = df_15.tail(lookback * 10)
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'))
            
            # Affichage de la zone et des lignes
            color_z = "rgba(0, 255, 0, 0.1)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.1)"
            fig.add_hrect(y0=p_stop, y1=swing_high if mode=="ACHAT (Long)" else swing_low, fillcolor=color_z, line_width=0, annotation_text="ZONE ACTION", annotation_position="top left")
            
            levels = {"Entrée (0.618)": p_entree, "Stop (0.786)": p_stop, "Sortie (1.618)": p_sortie}
            for label, val in levels.items():
                fig.add_hline(y=val, line_dash="dot", annotation_text=f"{label}: {val:.2f}$", annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
