import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro : Trend & Swing", layout="wide")
st.title("🏦 Terminal Expert : Analyse de Tendance & Swings Dynamiques")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
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
    return sum(conds), tenkan, kijun, sa, sb

def calculate_atr(data, period=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def find_dynamic_swings(data, mode_trade, atr_val):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    price_avg = data['Close'].mean()
    dynamic_dist = max(3, int((atr_val / price_avg) * 500)) 
    
    swings = []
    df_temp = data.copy().sort_values(by=col, ascending=(mode_trade == "VENTE (Short)"))
    
    for idx, row in df_temp.iterrows():
        if all(abs((idx - pd.to_datetime(s['Date'])).days) >= dynamic_dist for s in swings):
            swings.append({'Date': idx.strftime('%Y-%m-%d'), 'Prix': round(row[col], 2)})
        if len(swings) >= 2:
            break
    return pd.DataFrame(swings), dynamic_dist

# --- BOUTONS D'ACTION ---
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
            atr_v = calculate_atr(df_d).iloc[-1]

            # --- 1. DÉTECTION TENDANCE (NOUVEAU/RÉINTÉGRÉ) ---
            score_trend, _, _, sa_d, sb_d = get_ichimoku_score(df_d, "ACHAT (Long)")
            if score_trend >= 3:
                trend_label, trend_color = "HAUSSIER 📈", "#00FF00"
            elif score_trend <= 1:
                trend_label, trend_color = "BAISSIER 📉", "#FF0000"
            else:
                trend_label, trend_color = "NEUTRE ⚖️", "#FFA500"

            # --- 2. SWINGS DYNAMIQUES ---
            df_recent = df_d.tail(lookback)
            swings_df, dist_calculee = find_dynamic_swings(df_recent, mode, atr_v)
            swing_point = swings_df.iloc[0]['Prix']
            swing_date = swings_df.iloc[0]['Date']
            
            base_ref = df_recent['Low'].min() if mode == "ACHAT (Long)" else df_recent['High'].max()
            diff = abs(swing_point - base_ref)
            f_levels = {
                "0.5": swing_point - (0.5 * diff) if mode == "ACHAT (Long)" else swing_point + (0.5 * diff),
                "0.618": swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff),
                "0.786": swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff),
                "1.618": swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)
            }

            # --- 3. AFFICHAGE DES MÉTRIQUES ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label}</h3>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date du Pivot", swing_date, f"{swing_point:.2f} $")
            c2.metric("Score Ichimoku (D)", f"{score_trend}/4")
            c3.metric("Filtre Dynamique", f"{dist_calculee} jours")
            vol_ratio = df_15['Volume'].iloc[-1] / df_15['Volume'].rolling(20).mean().iloc[-1]
            c4.metric("Intensité Volume", f"{vol_ratio:.2f}x")
            st.divider()

            st.write("🔍 **Swings Majeurs (Ecart dynamique respecté) :**")
            st.table(swings_df)

            if btn_analyse:
                st.subheader("🚀 Diagnostic de Confluence")
                # Alerte si on trade contre la tendance
                if (mode == "ACHAT (Long)" and trend_label == "BAISSIER 📉") or (mode == "VENTE (Short)" and trend_label == "HAUSSIER 📈"):
                    st.warning(f"⚠️ ATTENTION : Tu tentes un trade en contre-tendance. Le marché est globalement {trend_label}.")
                
                en_zone = min(f_levels["0.5"], f_levels["0.786"]) <= px_actuel <= max(f_levels["0.5"], f_levels["0.786"])
                if en_zone and vol_ratio >= 1.2:
                    st.success("🎯 CONFLUENCE : Structure validée par le volume.")
                else:
                    st.info("🔭 Observation : En attente du signal optimal.")

            elif btn_anticipe:
                st.subheader("📈 Plan Stratégique")
                st.write(f"### Prix d'entrée (0.618) : **{f_levels['0.618']:.2f} $** | Objectif : **{f_levels['1.618']:.2f} $**")

            # --- 4. GRAPHIQUE ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku 15m (conduit)
            _, _, _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            
            # Fibonacci
            fig.add_hrect(y0=f_levels["0.786"], y1=f_levels["0.5"], fillcolor="rgba(0, 255, 0, 0.12)", line_width=0, annotation_text="ZONE ACTION", row=1, col=1)
            for lbl, val in f_levels.items():
