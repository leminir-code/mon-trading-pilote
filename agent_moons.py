import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Historical Tester", layout="wide")
st.title("🏦 Terminal Expert : Simulation Rétroactive & Risque")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="MSI").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)
    
    st.divider()
    st.header("🧪 Test Rétroactif")
    test_date = st.date_input("Date de début du test", value=datetime.now() - timedelta(days=15))

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

# --- BOUTONS ---
col_btn1, col_btn2, col_btn3 = st.columns(3)
btn_analyse = col_btn1.button("🚀 Analyser la Confluence")
btn_anticipe = col_btn2.button("📈 Plan de Trade & Risque")
btn_backtest = col_btn3.button("🧪 Simuler l'Entrée à Date")

if btn_analyse or btn_anticipe or btn_backtest:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]

            # --- 1. SMART SWING & FIBONACCI (CORRIGÉ) ---
            df_recent = df_d.tail(lookback)
            if mode == "ACHAT (Long)":
                swing_point = df_recent['High'].max()
                swing_date = df_recent['High'].idxmax().strftime('%d %b %Y')
                base_ref = df_recent['Low'].min()
            else:
                swing_point = df_recent['Low'].min()
                swing_date = df_recent['Low'].idxmin().strftime('%d %b %Y')
                base_ref = df_recent['High'].max()
            
            diff = abs(swing_point - base_ref)
            f_05 = swing_point - (0.5 * diff) if mode == "ACHAT (Long)" else swing_point + (0.5 * diff)
            f_0618 = swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff)
            f_0786 = swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff)
            f_target = swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)

            # --- 2. SCORES & ATR ---
            score_d, _, _, _, _ = get_ichimoku_score(df_d, mode)
            score_15, _, _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            atr_series = calculate_atr(df_15)
            atr_val = atr_series.iloc[-1]
            
            # --- 3. AFFICHAGE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date du Pivot", swing_date, f"{swing_point:.2f} $")
            c2.metric("Scores (D|15m)", f"{score_d}/4 | {score_15}/4")
            c3.metric("Capital", f"{capital:,.0f} $")
            c4.metric("ATR 15m", f"{atr_val:.2f}")
            st.divider()

            # --- MODULE RÉTROACTIF (NOUVEAU) ---
            if btn_backtest:
                st.subheader(f"🧪 Simulation d'entrée au {test_date}")
                hist_test = df_15[df_15.index >= pd.Timestamp(test_date)]
                
                if not hist_test.empty:
                    px_entree = hist_test['Open'].iloc[0]
                    dist_stop = abs(px_entree - f_0786)
                    quantite = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
                    investi = quantite * px_entree
                    
                    # Recherche du premier événement (Target ou Stop)
                    hit_target = hist_test[hist_test['High'] >= f_target] if mode == "ACHAT (Long)" else hist_test[hist_test['Low'] <= f_target]
                    hit_stop = hist_test[hist_test['Low'] <= f_0786] if mode == "ACHAT (Long)" else hist_test[hist_test['High'] >= f_0786]
                    
                    res_col1, res_col2 = st.columns(2)
                    res_col1.write(f"**Position :** {quantite} titres à {px_entree:.2f}$ (Total: {investi:,.2f}$)")
                    
                    if not hit_target.empty and (hit_stop.empty or hit_target.index[0] < hit_stop.index[0]):
                        gain = (f_target - px_entree) * quantite if mode == "ACHAT (Long)" else (px_entree - f_target) * quantite
                        st.success(f"🎯 RÉUSSITE : Objectif atteint le {hit_target.index[0].strftime('%d %b %Y')}. Gain estimé : **+{gain:,.2f} $**")
                    elif not hit_stop.empty:
                        perte = (px_entree - f_0786) * quantite if mode == "ACHAT (Long)" else (f_0786 - px_entree) * quantite
                        st.error(f"🛑 STOP LOSS : Niveau touché le {hit_stop.index[0].strftime('%d %b %Y')}. Perte : **-{perte:,.2f} $**")
                    else:
                        profit_latent = (px_actuel - px_entree) * quantite if mode == "ACHAT (Long)" else (px_entree - px_actuel) * quantite
                        st.info(f"⏳ EN COURS : Ni stop ni objectif touché. Profit/Perte actuel : {profit_latent:,.2f} $")
                else:
                    st.warning("Données insuffisantes pour cette date sur l'unité 15min.")

            # --- PLAN DE TRADE ---
            elif btn_anticipe:
                st.subheader("📈 Plan de Trade & Risque")
                dist = abs(f_0618 - f_0786)
                qty = int((capital * risk_pc) / dist) if dist > 0 else 0
                cp1, cp2, cp3 = st.columns(3)
                cp1.metric("Quantité suggérée", f"{qty} titres")
                cp2.metric("Engagement", f"{qty * f_0618:,.2f} $")
                cp3.metric("Profit Visé (%)", f"{((abs(f_target - f_0618)/f_0618)*100):.1f} %")

            # --- GRAPHIQUE ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'))
            
            # Ichimoku Kumo
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'))
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'))
            
            # Zones
            fig.add_hrect(y0=f_0786, y1=f_05, fillcolor="rgba(0, 255, 0, 0.1)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.1)", line_width=0, annotation_text="ZONE ACTION", annotation_position="top left")
            
            for label, val in {"ENTRÉE (0.618)": f_0618, "STOP (0.786)": f_0786, "CIBLE (1.618)": f_target}.items():
                fig.add_hline(y=val, line_dash="dot", line_color="rgba(255,255,255,0.4)", annotation_text=label, annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
