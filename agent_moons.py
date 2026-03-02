import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Intelligence MTF", layout="wide")
st.title("🏦 Terminal Expert : Multi-Timeframe & Vrai Swing")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre de recherche du Swing (jours)", 7, 90, 30)

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📈 Anticiper : Plan de Trade")

def get_ichimoku_score(data, mode_trade):
    """ Calcule le score Ichimoku (0-4) basé sur ton pseudo-code """
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
        c1 = px > max(sa.iloc[-1], sb.iloc[-1])
        c2 = sa.iloc[-1] > sb.iloc[-1]
        c3 = tenkan.iloc[-1] > kijun.iloc[-1]
        c4 = chikou_lib
    else:
        c1 = px < min(sa.iloc[-1], sb.iloc[-1])
        c2 = sa.iloc[-1] < sb.iloc[-1]
        c3 = tenkan.iloc[-1] < kijun.iloc[-1]
        c4 = chikou_lib
    return sum([c1, c2, c3, c4])

if btn_analyse or btn_anticipe:
    try:
        # DATA 1 : Daily pour la tendance de fond et le Swing
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        # DATA 2 : Intraday pour le timing
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            # --- 1. DÉTERMINATION DU VRAI SWING ---
            df_recent = df_d.tail(lookback)
            if mode == "ACHAT (Long)":
                swing_point = df_recent['High'].max()
                swing_date = df_recent['High'].idxmax().strftime('%Y-%m-%d')
                swing_low = df_recent['Low'].min() # Point de départ bas
                diff = swing_point - swing_low
                fibo_levels = { "0.5": swing_point - (0.5 * diff), "0.618": swing_point - (0.618 * diff), 
                                "0.786": swing_point - (0.786 * diff), "1.618": swing_point + (0.618 * diff) }
            else:
                swing_point = df_recent['Low'].min()
                swing_date = df_recent['Low'].idxmin().strftime('%Y-%m-%d')
                swing_high = df_recent['High'].max()
                diff = swing_high - swing_point
                fibo_levels = { "0.5": swing_point + (0.5 * diff), "0.618": swing_point + (0.618 * diff), 
                                "0.786": swing_point + (0.786 * diff), "1.618": swing_point - (0.618 * diff) }

            px_actuel = df_15['Close'].iloc[-1]

            # --- 2. SCORES MULTI-TIMEFRAME ---
            score_d = get_ichimoku_score(df_d, mode)
            score_15 = get_ichimoku_score(df_15, mode)

            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Swing détecté le", swing_date, f"{swing_point:.2f} $")
            c2.metric("Score DAILY", f"{score_d}/4", delta="Tendance Fond")
            c3.metric("Score 15 MIN", f"{score_15}/4", delta="Timing Entrée")
            st.divider()

            # --- 3. LOGIQUE DES BOUTONS (PLAN DE TRADE) ---
            if btn_analyse:
                if score_d >= 3 and score_15 >= 3:
                    st.success("🔥 ALIGNEMENT TOTAL : Les deux horizons de temps confirment le mouvement.")
                elif score_d >= 3:
                    st.warning("⚠️ ATTENTION : Tendance haussière en Daily, mais repli en cours sur 15m. Attendez le signal intraday.")
                else:
                    st.info("🔭 Pas d'alignement. Observez le prix.")

            elif btn_anticipe:
                st.subheader("🎯 Plan d'Anticipation")
                p_entree = fibo_levels["0.618"]
                p_target = fibo_levels["1.618"]
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if px_actuel > p_entree and mode == "ACHAT (Long)":
                        st.info(f"⏳ Attente de retour en zone d'achat vers {p_entree:.2f} $")
                    else:
                        st.success(f"🚀 Zone de trade active. Cible : {p_target:.2f} $")
                with col_b:
                    st.metric("Profit potentiel", f"{((p_target/p_entree)-1)*100:.1f}%")

            # --- 4. GRAPHIQUE OPTIMISÉ ---
            # On n'affiche que la période spécifiée par lookback sur l'intraday
            df_plot = df_15.tail(lookback * 20) # Approx pour couvrir les jours de bourse
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku sur le plot
            h9p, l9p = df_plot['High'].rolling(9).max(), df_plot['Low'].rolling(9).min()
            tenkan_p = (h9p + l9p) / 2
            h26p, l26p = df_plot['High'].rolling(26).max(), df_plot['Low'].rolling(26).min()
            kijun_p = (h26p + l26p) / 2
            sa_p = ((tenkan_p + kijun_p) / 2).shift(26)
            sb_p = ((df_plot['High'].rolling(52).max() + df_plot['Low'].rolling(52).min()) / 2).shift(26)

            fig.add_trace(go.Scatter(x=df_plot.index, y=sa_p, line=dict(color='rgba(0, 255, 0, 0.1)'), name='SA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=sb_p, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=tenkan_p, line=dict(color='#00FFFF', width=1), name='Tenkan'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=kijun_p, line=dict(color='#FFFF00', width=1), name='Kijun'), row=1, col=1)

            # Zone Fibonacci et Prix
            color_zone = "rgba(0, 255, 0, 0.1)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.1)"
            fig.add_hrect(y0=fibo_levels["0.786"], y1=fibo_levels["0.5"], fillcolor=color_zone, line_width=0, annotation_text="ZONE D'ENTRÉE", annotation_position="top left", row=1, col=1)
            
            for label, val in fibo_levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color="rgba(255,255,255,0.3)", annotation_text=f"{label}: {val:.2f}$", annotation_position="bottom right", row=1, col=1)

            # Volume
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume'), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
