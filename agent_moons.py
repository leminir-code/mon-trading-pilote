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
    lookback_max = st.slider("Fenêtre Max du Swing (jours)", 15, 120, 60)

# --- FONCTIONS TECHNIQUES (CONSERVÉES) ---
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

# --- BOUTONS D'ACTION (2 BOUTONS) ---
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
            
            # 1. SWINGS DYNAMIQUES & FIBONACCI
            swings_df, dist_calculee = find_dynamic_swings(df_recent, mode, atr_d)
            swing_point = swings_df.iloc[0]['Prix']
            base_ref = df_recent['Low'].min() if mode == "ACHAT (Long)" else df_recent['High'].max()
            diff = abs(swing_point - base_ref)
            
            f_0618 = swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff)
            f_0786 = swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff)
            f_stop = swing_point - (0.95 * diff) if mode == "ACHAT (Long)" else swing_point + (0.95 * diff)
            f_target = swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)

            # 2. TENDANCE & VOLUME
            score_trend, sa_d, sb_d = get_ichimoku_score(df_d, mode)
            trend_label = "HAUSSIER 📈" if score_trend >= 3 else "BAISSIER 📉" if score_trend <= 1 else "NEUTRE ⚖️"
            trend_color = "#00FF00" if trend_label == "HAUSSIER 📈" else "#FF0000" if trend_label == "BAISSIER 📉" else "#FFA500"
            vol_moyen = df_15['Volume'].rolling(20).mean().iloc[-1]
            vol_ratio = df_15['Volume'].iloc[-1] / vol_moyen

            # --- AFFICHAGE MÉTRIQUES (4 EN LIGNE) ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label}</h3>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date du Pivot", swings_df.iloc[0]['Date'], f"{swing_point:.2f} $")
            c2.metric("Prix Entrée (0.618)", f"{f_0618:.2f} $")
            c3.metric("Prix Vente (Cible)", f"{f_target:.2f} $", delta=f"{((f_target/f_0618-1)*100):.1f}%")
            c4.metric("Filtre Dynamique", f"{dist_calculee} jrs")
            st.divider()

            # --- DIFFÉRENCIATION DES SORTIES BOUTONS ---
            if btn_analyse:
                st.subheader("🚀 Diagnostic de Confluence")
                c_diag1, c_diag2 = st.columns(2)
                with c_diag1:
                    if vol_ratio >= 1.2: st.success(f"✅ Volume puissant ({vol_ratio:.2f}x)")
                    else: st.warning(f"⚠️ Volume faible ({vol_ratio:.2f}x)")
                with c_diag2:
                    if score_trend >= 3: st.success(f"✅ Tendance Ichimoku confirmée ({score_trend}/4)")
                    else: st.error(f"❌ Tendance fragile ({score_trend}/4)")
                st.write("**Tableau des 2 derniers Swings :**")
                st.table(swings_df)

            elif btn_anticipe:
                st.subheader("📋 Ticket d'Ordre Courtage (Investissement : 10 000 $)")
                qty = int((capital * risk_pc) / abs(f_0618 - f_stop)) if abs(f_0618 - f_stop) > 0 else 0
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.info(f"**ORDRE ACHAT**\n- **Quantité :** {qty} titres\n- **Prix Limit :** {f_0618:.2f} $\n- **Zone Soldes :** {f_0786:.2f} $")
                with col_t2:
                    st.success(f"**ORDRE VENTE**\n- **Objectif (Profit) :** {f_target:.2f} $\n- **Stop Loss :** {f_stop:.2f} $")

            # --- 4. GRAPHIQUE COMPLET (CLOUD + VOLUME + LABELS GAUCHE) ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku Cloud 15m
            _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            
            # Fibonacci & Zones (Labels à GAUCHE)
            fig.add_hrect(y0=f_stop, y1=f_0618, fillcolor="rgba(255, 0, 0, 0.05)", line_width=0, annotation_text="ZONE RISQUE", annotation_position="top left", row=1, col=1)
            fig.add_hrect(y0=f_0618, y1=f_target, fillcolor="rgba(0, 255, 0, 0.05)", line_width=0, annotation_text="ZONE PROFIT", annotation_position="top left", row=1, col=1)
            
            levels = {"ENTRÉE": f_0618, "SOLDES": f_0786, "STOP": f_stop, "VENTE": f_target}
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
