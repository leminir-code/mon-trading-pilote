import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro : Analyse Flux & Ichimoku", layout="wide")
st.title("🏦 Terminal Expert : Volume, Ichimoku & Swings Dynamiques")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="META").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback_max = st.slider("Fenêtre Max du Swing (jours)", 15, 120, 60)

# --- FONCTIONS TECHNIQUES (ICHIMOKU & VOLATILITÉ) ---
def get_ichimoku_score(data, mode_trade):
    if len(data) < 52: return 0, None, None, None, None
    px = data['Close'].iloc[-1]
    
    # Tenkan-sen (9-period high + 9-period low) / 2
    h9, l9 = data['High'].rolling(9).max(), data['Low'].rolling(9).min()
    tenkan = (h9 + l9) / 2
    
    # Kijun-sen (26-period high + 26-period low) / 2
    h26, l26 = data['High'].rolling(26).max(), data['Low'].rolling(26).min()
    kijun = (h26 + l26) / 2
    
    # Senkou Span A (Tenkan + Kijun) / 2, shifted 26 periods ahead
    sa = ((tenkan + kijun) / 2).shift(26)
    
    # Senkou Span B (52-period high + 52-period low) / 2, shifted 26 periods ahead
    sb = ((data['High'].rolling(52).max() + data['Low'].rolling(52).min()) / 2).shift(26)
    
    # Chikou Span (Current close shifted back 26 periods)
    chikou_lib = px > data['Close'].shift(26).iloc[-1] if mode_trade == "ACHAT (Long)" else px < data['Close'].shift(26).iloc[-1]
    
    # Calcul du score de confluence
    if mode_trade == "ACHAT (Long)":
        conds = [
            px > max(sa.iloc[-1], sb.iloc[-1]), # Prix au-dessus du nuage
            sa.iloc[-1] > sb.iloc[-1],          # Nuage vert (A > B)
            tenkan.iloc[-1] > kijun.iloc[-1],   # Tenkan > Kijun
            chikou_lib                          # Chikou libre
        ]
    else:
        conds = [
            px < min(sa.iloc[-1], sb.iloc[-1]), # Prix en-dessous du nuage
            sa.iloc[-1] < sb.iloc[-1],          # Nuage rouge (A < B)
            tenkan.iloc[-1] < kijun.iloc[-1],   # Tenkan < Kijun
            chikou_lib                          # Chikou libre
        ]
    return sum(conds), sa, sb

def calculate_atr(data, period=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    return np.max(ranges, axis=1).rolling(period).mean()

def find_dynamic_swings(data, mode_trade, atr_val):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    price_avg = data['Close'].mean()
    dynamic_dist = max(3, int((atr_val / price_avg) * 500)) 
    swings = []
    df_temp = data.copy().sort_values(by=col, ascending=(mode_trade == "VENTE (Short)"))
    for idx, row in df_temp.iterrows():
        if all(abs((idx - pd.to_datetime(s['Date'])).days) >= dynamic_dist for s in swings):
            swings.append({'Date': idx.strftime('%Y-%m-%d'), 'Prix': round(row[col], 2)})
        if len(swings) >= 2: break
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
            atr_d = calculate_atr(df_d).iloc[-1]
            df_recent = df_d.tail(lookback_max)
            
            # --- 1. DÉTECTION SWINGS DYNAMIQUES ---
            swings_df, dist_calculee = find_dynamic_swings(df_recent, mode, atr_d)
            swing_point = swings_df.iloc[0]['Prix']
            base_ref = df_recent['Low'].min() if mode == "ACHAT (Long)" else df_recent['High'].max()
            diff = abs(swing_point - base_ref)
            
            # Niveaux Fibonacci
            f_entree = swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff)
            f_soldes = swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff)
            f_stop = swing_point - (0.95 * diff) if mode == "ACHAT (Long)" else swing_point + (0.95 * diff)
            f_target = swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)

            # --- 2. ICHIMOKU & VOLUME ---
            score_trend, sa_d, sb_d = get_ichimoku_score(df_d, mode)
            trend_label = "HAUSSIER 📈" if score_trend >= 3 else "BAISSIER 📉" if score_trend <= 1 else "NEUTRE ⚖️"
            trend_color = "#00FF00" if "HAUSSIER" in trend_label else "#FF0000" if "BAISSIER" in trend_label else "#FFA500"
            
            vol_moyen = df_15['Volume'].rolling(20).mean().iloc[-1]
            vol_actuel = df_15['Volume'].iloc[-1]

            # --- 3. AFFICHAGE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label} (Ichimoku: {score_trend}/4)</h3>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Dernier Pivot", swings_df.iloc[0]['Date'], f"{swing_point:.2f} $")
            c2.metric("Entrée (0.618)", f"{f_entree:.2f} $")
            c3.metric("Objectif (TP)", f"{f_target:.2f} $", delta=f"{((f_target/f_entree-1)*100):.1f}%")
            c4.metric("Vol. vs Moyenne", f"{(vol_actuel/vol_moyen):.1f}x")
            st.divider()

            st.write("🔍 **Tableau des 2 derniers Swings (Écart dynamique ATR) :**")
            st.table(swings_df)

            if btn_anticipe:
                st.subheader("📋 Ticket pour ta plateforme de courtage")
                qty = int((capital * risk_pc) / abs(f_entree - f_stop)) if abs(f_entree - f_stop) > 0 else 0
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.info(f"**ORDRE ACHAT**\n- **Quantité :** {qty}\n- **Prix Limit :** {f_entree:.2f} $\n- **Zone Soldes :** {f_soldes:.2f} $")
                with col_t2:
                    st.success(f"**ORDRE VENTE**\n- **Take Profit :** {f_target:.2f} $\n- **Stop Loss :** {f_stop:.2f} $")

            # --- 4. GRAPHIQUE (LABELS À GAUCHE) ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            
            # Candlestick
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku Cloud 15m (Rétabli)
            _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            
            # Zones Visuelles
            fig.add_hrect(y0=f_stop, y1=f_entree, fillcolor="rgba(255, 0, 0, 0.05)", line_width=0, annotation_text="RISQUE", annotation_position="top left", row=1, col=1)
            fig.add_hrect(y0=f_entree, y1=f_target, fillcolor="rgba(0, 255, 0, 0.05)", line_width=0, annotation_text="INTERVENTION", annotation_position="top left", row=1, col=1)
            
            # Niveaux Fib (Labels Gauche)
            levels = {"ENTRÉE": f_entree, "SOLDES": f_soldes, "STOP": f_stop, "VENTE": f_target}
            colors = {"ENTRÉE": "cyan", "SOLDES": "yellow", "STOP": "red", "VENTE": "#00FF00"}
            for lbl, val in levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color=colors[lbl], annotation_text=f"{lbl}: {val:.2f}$", annotation_position="top left", row=1, col=1)

            # Volume (Rétabli)
            v_colors = ['#26a69a' if c >= o else '#ef5350' for o, c in zip(df_plot['Open'], df_plot['Close'])]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors, name='Volume'), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
