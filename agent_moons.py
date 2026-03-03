import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro : Ordres de Bourse", layout="wide")
st.title("🏦 Terminal Expert : Stratégie d'Entrée & Objectifs de Vente")

with st.sidebar:
    st.header("⚙️ Paramètres du Compte")
    ticker = st.text_input("🔍 Symbole", value="META").upper()
    capital = st.number_input("💰 Capital disponible ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par Trade (%)", 0.5, 5.0, 1.0) / 100
    
    st.divider()
    mode = st.radio("Direction souhaitée", ["ACHAT (Long)", "VENTE (Short)"])
    lookback = st.slider("Analyse du Swing (jours)", 7, 120, 60)

# --- FONCTIONS TECHNIQUES ---
def get_ichimoku_score(data, mode_trade):
    if len(data) < 52: return 0, None, None, None, None
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
    return sum(conds), sa, sb

def find_dynamic_swings(data, mode_trade):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    idx = data[col].idxmax() if mode_trade == "ACHAT (Long)" else data[col].idxmin()
    return idx, data.loc[idx, col]

# --- BOUTONS D'ACTION (CONSERVÉS) ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser la Tendance")
btn_plan = col_btn2.button("📈 Générer le Plan d'Exécution")

if btn_analyse or btn_plan:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]
            
            # 1. TENDANCE ET SWINGS
            score_trend, sa_d, sb_d = get_ichimoku_score(df_d, "ACHAT (Long)")
            trend_label = "HAUSSIER 📈" if score_trend >= 3 else "BAISSIER 📉" if score_trend <= 1 else "NEUTRE ⚖️"
            trend_color = "#00FF00" if "HAUSSIER" in trend_label else "#FF0000" if "BAISSIER" in trend_label else "#FFA500"

            swing_idx, swing_val = find_dynamic_swings(df_d.tail(lookback), mode)
            base_ref = df_d.tail(lookback)['Low'].min() if mode == "ACHAT (Long)" else df_d.tail(lookback)['High'].max()
            diff = abs(swing_val - base_ref)

            # NIVEAUX DE PRIX PRÉCIS
            p_entree = swing_val - (0.618 * diff) if mode == "ACHAT (Long)" else swing_val + (0.618 * diff)
            p_soldes = swing_val - (0.786 * diff) if mode == "ACHAT (Long)" else swing_val + (0.786 * diff)
            p_stop = swing_val - (0.90 * diff) if mode == "ACHAT (Long)" else swing_val + (0.90 * diff)
            p_vente = swing_val + (0.618 * diff) if mode == "ACHAT (Long)" else swing_val - (0.618 * diff) # Extension 1.618

            # 2. AFFICHAGE DES MÉTRIQUES
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label}</h3>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prix Entrée (0.618)", f"{p_entree:.2f} $")
            c2.metric("Prix Soldes (0.786)", f"{p_soldes:.2f} $")
            c3.metric("Indication Vente", f"{p_vente:.2f} $", delta=f"{((p_vente/p_entree-1)*100):.1f}%")
            c4.metric("Score Tendance", f"{score_trend}/4")
            st.divider()

            # 3. PLAN D'EXÉCUTION ET QUANTITÉ
            if btn_plan:
                # Calcul quantité basée sur le risque
                risk_amt = capital * risk_pc
                qty = int(risk_amt / abs(p_entree - p_stop)) if abs(p_entree - p_stop) > 0 else 0
                
                st.subheader("📋 Ticket d'Ordre Automatique")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.info(f"""
                    **PARAMÈTRES D'ACHAT**
                    - **Action :** {ticker}
                    - **Type :** BUY LIMIT
                    - **Prix d'entrée :** {p_entree:.2f} $
                    - **Quantité :** {qty} titres
                    - **Investissement :** {(qty * p_entree):,.2f} $
                    """)
                with col_t2:
                    st.success(f"""
                    **PARAMÈTRES DE SORTIE**
                    - **Vente (Objectif) :** {p_vente:.2f} $
                    - **Stop Loss :** {p_stop:.2f} $
                    - **Profit Potentiel :** {(qty * abs(p_vente - p_entree)):,.2f} $
                    - **Ratio R/R :** {abs(p_vente - p_entree) / abs(p_entree - p_stop):.2f}
                    """)

            # 4. GRAPHIQUE PROFESSIONNEL
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'))
            
            # Zones
            fig.add_hrect(y0=p_stop, y1=p_entree, fillcolor="rgba(255, 0, 0, 0.05)", line_width=0, annotation_text="ZONE DE RISQUE")
            fig.add_hrect(y0=p_entree, y1=p_vente, fillcolor="rgba(0, 255, 0, 0.05)", line_width=0, annotation_text="ZONE DE PROFIT")
            
            # Lignes Fibonacci
            levels = {"ENTRÉE": p_entree, "SOLDES": p_soldes, "STOP": p_stop, "VENTE (Cible)": p_vente}
            colors = {"ENTRÉE": "cyan", "SOLDES": "yellow", "STOP": "red", "VENTE (Cible)": "#00FF00"}
            
            for lbl, val in levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color=colors[lbl], annotation_text=f"{lbl}: {val:.2f}$", annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=750, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
