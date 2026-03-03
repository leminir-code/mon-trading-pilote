import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro : Intelligence Flux", layout="wide")
st.title("🏦 Terminal Expert : Smart Swing & Plan d'Exécution")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="META").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 120, 60)

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

def find_top_swings(data, mode_trade, n=2):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    swings = []
    df_temp = data.copy()
    for _ in range(n):
        idx = df_temp[col].idxmax() if mode_trade == "ACHAT (Long)" else df_temp[col].idxmin()
        swings.append({'Date': idx.strftime('%Y-%m-%d'), 'Prix': round(df_temp.loc[idx, col], 2)})
        df_temp = df_temp.drop(index=idx)
    return pd.DataFrame(swings)

# --- BOUTONS D'ACTION (CONSERVÉS) ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser la Confluence")
btn_anticipe = col_btn2.button("📈 Anticiper : Plan de Trade")

if btn_analyse or btn_anticipe:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]
            swings_df = find_top_swings(df_d.tail(lookback), mode)
            
            # --- CALCULS FIBONACCI ---
            swing_point = swings_df.iloc[0]['Prix']
            base_ref = df_d.tail(lookback)['Low'].min() if mode == "ACHAT (Long)" else df_d.tail(lookback)['High'].max()
            diff = abs(swing_point - base_ref)
            
            f_0618 = swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff)
            f_0786 = swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff)
            f_stop = swing_point - (0.90 * diff) if mode == "ACHAT (Long)" else swing_point + (0.90 * diff)
            f_target = swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)

            # --- TENDANCE ---
            score_trend, _, _ = get_ichimoku_score(df_d, "ACHAT (Long)")
            trend_label = "HAUSSIER 📈" if score_trend >= 3 else "BAISSIER 📉" if score_trend <= 1 else "NEUTRE ⚖️"
            trend_color = "#00FF00" if "HAUSSIER" in trend_label else "#FF0000" if "BAISSIER" in trend_label else "#FFA500"

            # --- AFFICHAGE MÉTRIQUES (RÉTABLI) ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label}</h3>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date du Pivot", swings_df.iloc[0]['Date'], f"{swing_point:.2f} $")
            c2.metric("Prix Entrée (0.618)", f"{f_0618:.2f} $")
            c3.metric("Prix Vente (Cible)", f"{f_target:.2f} $", delta=f"{((f_target/f_0618-1)*100):.1f}%")
            c4.metric("Score Tendance", f"{score_trend}/4")
            st.divider()

            st.write("🔍 **Derniers Swings identifiés (pour tes tests historiques) :**")
            st.table(swings_df)

            if btn_anticipe:
                st.subheader("📉 Plan Stratégique & Quantité")
                qty = int((capital * risk_pc) / abs(f_0618 - f_stop))
                st.success(f"### Ordre suggéré : Acheter **{qty}** titres à **{f_0618:.2f} $**")
                st.write(f"**Stop Loss de sécurité :** {f_stop:.2f} $ | **Objectif de Vente :** {f_target:.2f} $")

            # --- 4. GRAPHIQUE COMPLET (CLOUD + VOLUME RÉTABLIS) ---
            df_plot = df_15.tail(600)
            vol_moyen = df_15['Volume'].rolling(20).mean().iloc[-1]
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # Candlesticks
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku Cloud 15m
            _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            
            # Fibonacci Levels
            f_levels = {"ENTRÉE": f_0618, "SOLDES": f_0786, "STOP": f_stop, "VENTE": f_target}
            colors = {"ENTRÉE": "cyan", "SOLDES": "yellow", "STOP": "red", "VENTE": "#00FF00"}
            for lbl, val in f_levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color=colors[lbl], annotation_text=f"{lbl}: {val:.2f}$", annotation_position="bottom right", row=1, col=1)

            # Volume Plot
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_plot['Volume']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors, name='Volume'), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
