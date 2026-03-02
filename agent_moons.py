import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Terminal Moons Intelligence Pro", layout="wide")
st.title("🏦 Terminal Expert : Stratégie Multi-Horizon & Volume")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)

# --- FONCTION SCORE ICHIMOKU (MULTI-TIMEFRAME) ---
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
    return sum(conds), tenkan, kijun, sa, sb

# --- BOUTONS D'ACTION ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📈 Anticiper : Plan de Trade")

if btn_analyse or btn_anticipe:
    try:
        # Données Daily (Swing) et 15min (Timing)
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            # --- 1. CALCULS SWING & FIBONACCI ---
            df_recent = df_d.tail(lookback)
            swing_high = df_recent['High'].max()
            swing_low = df_recent['Low'].min()
            diff = swing_high - swing_low
            px_actuel = df_15['Close'].iloc[-1]

            # Niveaux selon le mode
            if mode == "ACHAT (Long)":
                f_05, f_0618, f_0786 = swing_high - (0.5 * diff), swing_high - (0.618 * diff), swing_high - (0.786 * diff)
                f_target = swing_high + (0.618 * diff) # Extension 1.618
            else:
                f_05, f_0618, f_0786 = swing_low + (0.5 * diff), swing_low + (0.618 * diff), swing_low + (0.786 * diff)
                f_target = swing_low - (0.618 * diff)

            # --- 2. SCORES & VOLUME ---
            score_d, _, _, _, _ = get_ichimoku_score(df_d, mode)
            score_15, tk_15, kj_15, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            market_trend = "BULL 🟢" if score_d >= 3 else "BEAR 🔴"
            
            vol_actuel = df_15['Volume'].iloc[-1]
            vol_moyen = df_15['Volume'].rolling(20).mean().iloc[-1]
            ratio_vol = vol_actuel / vol_moyen

            # --- 3. AFFICHAGE DES RÉSULTATS ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $ ({market_trend})</h1>", unsafe_allow_html=True)
            
            c_inf1, c_inf2, c_inf3 = st.columns(3)
            c_inf1.metric("Score DAILY", f"{score_d}/4")
            c_inf2.metric("Score 15 MIN", f"{score_15}/4")
            c_inf3.metric("Intensité Volume", f"{ratio_vol:.2f}x")
            st.divider()

            if btn_analyse:
                st.subheader("🚀 Diagnostic du Signal")
                en_zone = min(f_05, f_0786) <= px_actuel <= max(f_05, f_0786)
                if en_zone and ratio_vol > 1.2: st.success("✅ CONFLUENCE : Prix en zone avec volume validé.")
                else: st.info("🔭 Observation : En attente de confluence.")

            elif btn_anticipe:
                st.subheader("📉 Plan Stratégique Bear/Bull")
                col_strat1, col_strat2 = st.columns(2)
                
                with col_strat1:
                    st.write("### 🎯 Recommandation Entrée")
                    if market_trend == "BEAR 🔴":
                        st.error(f"Marché Bear : Attendez les soldes à **{f_0618:.2f} $** pour acheter.")
                    else:
                        st.success(f"Marché Bull : Entrée idéale à **{f_0618:.2f} $** (0.618 Fibo).")
                
                with col_strat2:
                    st.write("### 💰 Objectif de Sortie")
                    if market_trend == "BULL 🟢":
                        st.info(f"Vendre à l'extension Fibonacci 1.618 : **{f_target:.2f} $**.")
                    else:
                        st.warning(f"Sortie de secours conseillée à **{f_target:.2f} $**.")

            # --- 4. GRAPHIQUE COMPLET ---
            df_plot = df_15.tail(lookback * 12)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # Chandeliers & Ichimoku
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.2)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.2)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=tk_15, line=dict(color='#00FFFF', width=1), name='Tenkan'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=kj_15, line=dict(color='#FFFF00', width=1), name='Kijun'), row=1, col=1)

            # Zone Pastel à Gauche
            color_z = "rgba(0, 255, 0, 0.12)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.12)"
            fig.add_hrect(y0=f_0786, y1=f_05, fillcolor=color_z, line_width=0, annotation_text="ZONE ACTION", annotation_position="top left", row=1, col=1)
            
            # Fibonacci avec Prix à Droite
            levels = {"0.5": f_05, "0.618": f_0618, "0.786": f_0786, "SORTIE 1.618": f_target}
            for label, val in levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color="rgba(255,255,255,0.3)", annotation_text=f"{label}: {val:.2f}$", annotation_position="bottom right", row=1, col=1)

            # Volume
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_plot['Volume']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors, name='Volume'), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
