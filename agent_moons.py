import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro : Intelligence Flux", layout="wide")
st.title("🏦 Terminal Expert : Gestion Multi-Cibles & Sécurité")

# --- DOCUMENTATION & ALGORITHME (COMPLET) ---
with st.expander("📖 DOCUMENTATION & ALGORITHME DE L'AGENT"):
    st.markdown("""
    ### 🛡️ Algorithme de Détection Dynamique
    1. **Synchronisation Temporelle** : Correction des fuseaux horaires (UTC) pour éviter les erreurs de comparaison.
    2. **Scan ATR** : Calcul de la volatilité pour définir l'écart minimum (C4).
    3. **Détection Temporelle** : Identification des pivots majeurs sur 1 an.
    4. **Projection Graphique** : Marquage visuel des dates de pivot sur le flux 15 min.
    """)

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="NVDA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 5.0) / 100
    lookback_max = st.slider("Fenêtre Max du Swing (jours)", 15, 120, 91)

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
    conds = [px > max(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] > sb.iloc[-1], tenkan.iloc[-1] > kijun.iloc[-1], chikou_lib] if mode_trade == "ACHAT (Long)" else [px < min(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] < sb.iloc[-1], tenkan.iloc[-1] < kijun.iloc[-1], chikou_lib]
    return sum(conds), sa, sb

def find_dynamic_swings(data, mode_trade, atr_val):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    price_avg = data['Close'].mean()
    dynamic_dist = max(3, int((atr_val / price_avg) * 500)) 
    swings = []
    df_temp = data.copy().sort_values(by=col, ascending=(mode_trade == "VENTE (Short)"))
    for idx, row in df_temp.iterrows():
        # Correction TZ : On s'assure que les dates sont TZ-naive pour la comparaison
        if all(abs((idx.replace(tzinfo=None) - pd.to_datetime(s['Date']).replace(tzinfo=None)).days) >= dynamic_dist for s in swings):
            swings.append({'Date': idx.strftime('%Y-%m-%d %H:%M:%S'), 'Prix': round(row[col], 2)})
        if len(swings) >= 2: break
    return pd.DataFrame(swings), dynamic_dist

# --- LOGIQUE DE CALCUL ---
try:
    df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
    df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
    
    if not df_d.empty and not df_15.empty:
        if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
        if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

        px_actuel = df_15['Close'].iloc[-1]
        atr_d = (df_d['High'] - df_d['Low']).rolling(14).mean().iloc[-1]
        swings_df, dist_calculee = find_dynamic_swings(df_d.tail(lookback_max), mode, atr_d)
        
        t1_pivot = swings_df.iloc[0]['Prix'] 
        base_ref = df_d.tail(lookback_max)['Low'].min() if mode == "ACHAT (Long)" else df_d.tail(lookback_max)['High'].max()
        diff = abs(t1_pivot - base_ref)
        
        f_entree = t1_pivot - (0.618 * diff) if mode == "ACHAT (Long)" else t1_pivot + (0.618 * diff)
        f_soldes = t1_pivot - (0.786 * diff) if mode == "ACHAT (Long)" else t1_pivot + (0.786 * diff)
        f_stop = t1_pivot - (0.95 * diff) if mode == "ACHAT (Long)" else t1_pivot + (0.95 * diff)
        
        score_trend, sa_d, sb_d = get_ichimoku_score(df_d, mode)
        trend_label = "HAUSSIER 📈" if score_trend >= 3 else "BAISSIER 📉" if score_trend <= 1 else "NEUTRE ⚖️"
        trend_color = "#00FF00" if trend_label == "HAUSSIER 📈" else "#FF0000" if trend_label == "BAISSIER 📉" else "#FFA500"

        tp2_final = t1_pivot + (0.618 * diff) if mode == "ACHAT (Long)" else t1_pivot - (0.618 * diff)
        tp1_secure = (f_entree + tp2_final) / 2
        tp3_max = t1_pivot + (1.618 * diff) if mode == "ACHAT (Long)" else t1_pivot - (1.618 * diff)
        qty = int((capital * risk_pc) / abs(f_entree - f_stop)) if abs(f_entree - f_stop) > 0 else 0

        # --- INTERFACE ---
        st.divider()
        st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label} (Score Ichimoku: {score_trend}/4)</h3>", unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("C1 (T1 Valeur Pivot)", swings_df.iloc[0]['Date'][:10], f"{t1_pivot:.2f} $")
        c2.metric("C2 (Prix d'entrée)", f"{f_entree:.2f} $")
        c3.metric("C3 (Prix de vente)", f"{tp2_final:.2f} $")
        c4.metric("C4 (Filtre Dynamique)", f"{dist_calculee} jrs")
        
        st.divider()
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        if col_btn1.button("🚀 Analyser la Confluence"): st.table(swings_df)
        if col_btn2.button("📈 Anticiper : Plan de Trade"):
            st.info(f"Entrée: {f_entree:.2f}$ | Qty: {qty} | TP1: {tp1_secure:.2f}$ | TP2: {tp2_final:.2f}$ | TP3: {tp3_max:.2f}$ | Stop: {f_stop:.2f}$")
        
        # FICHE DE COURTAGE COMPLÈTE
        if col_btn3.button("📋 Voir la Fiche"):
            fiche_df = pd.DataFrame({
                "Paramètre Courtage": ["Quantité (Qty)", "Prix d'Entrée (C2)", "Objectif Sécurisé (TP1)", "Objectif Principal (TP2)", "Objectif Profit Max (TP3)", "Stop Loss"],
                "Valeur": [qty, f"{f_entree:.2f} $", f"{tp1_secure:.2f} $", f"{tp2_final:.2f} $", f"{tp3_max:.2f} $", f"{f_stop:.2f} $"]
            })
            st.table(fiche_df)

        # --- GRAPHIQUE AMÉLIORÉ ---
        df_plot = df_15.tail(600)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
        
        for idx, row in swings_df.iterrows():
            # Harmonisation TZ pour le tracé
            swing_dt = pd.to_datetime(row['Date']).replace(tzinfo=df_plot.index.tzinfo)
            if swing_dt >= df_plot.index.min():
                fig.add_vline(x=swing_dt, line_dash="dash", line_color="white", row=1, col=1)
                fig.add_annotation(x=swing_dt, y=row['Prix'], text=f"PIVOT {row['Date'][:10]}", showarrow=True, row=1, col=1)

        levels = {"T1": t1_pivot, "C2": f_entree, "SOLDES": f_soldes, "TP1": tp1_secure, "TP2": tp2_final, "TP3": tp3_max, "STOP": f_stop}
        colors = {"T1": "white", "C2": "cyan", "SOLDES": "yellow", "TP1": "#FFA500", "TP2": "#00FF00", "TP3": "#00FFFF", "STOP": "red"}
        for lbl, val in levels.items():
            fig.add_hline(y=val, line_dash="dot", line_color=colors[lbl], annotation_text=f"{lbl}: {val:.2f}$", annotation_position="top left", row=1, col=1)

        _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
        fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
        
        fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
