import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Terminal Moons Intelligence Totale", layout="wide")
st.title("🏦 Terminal Expert : Analyse, Risque & Simulation Rétroactive")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="MSI").upper()
    capital = st.number_input("💰 Capital d'investissement ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)
    
    st.divider()
    st.info("💡 L'agent détecte automatiquement le dernier swing majeur pour tes tests.")

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
    return sum(conds), tenkan, kijun, sa, sb

def calculate_atr(data, period=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

# --- BOUTONS D'ACTION ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser la Confluence")
btn_backtest = col_btn2.button("🧪 Tester la Stratégie sur ce Swing")

if btn_analyse or btn_backtest:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]

            # --- 1. DÉTECTION DU DERNIER SWING ---
            df_recent = df_d.tail(lookback)
            if mode == "ACHAT (Long)":
                swing_point = df_recent['High'].max()
                swing_date_idx = df_recent['High'].idxmax()
                base_ref = df_recent['Low'].min()
            else:
                swing_point = df_recent['Low'].min()
                swing_date_idx = df_recent['Low'].idxmin()
                base_ref = df_recent['High'].max()
            
            diff = abs(swing_point - base_ref)
            f_05 = swing_point - (0.5 * diff) if mode == "ACHAT (Long)" else swing_point + (0.5 * diff)
            f_0618 = swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff)
            f_0786 = swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff)
            f_target = swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)

            # --- 2. SCORES, VOLUME & ATR ---
            score_d, _, _, _, _ = get_ichimoku_score(df_d, mode)
            score_15, _, _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            vol_actuel = df_15['Volume'].iloc[-1]
            vol_moyen = df_15['Volume'].rolling(20).mean().iloc[-1]
            ratio_vol = vol_actuel / vol_moyen
            atr_series = calculate_atr(df_15)
            atr_val = atr_series.iloc[-1]

            # --- 3. AFFICHAGE DES MÉTRIQUES (FORMAT CONSERVÉ) ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date du Pivot", swing_date_idx.strftime('%d %b %Y'), f"{swing_point:.2f} $")
            c2.metric("Scores (D|15m)", f"{score_d}/4 | {score_15}/4")
            c3.metric("Intensité Volume", f"{ratio_vol:.2f}x")
            c4.metric("ATR 15m", f"{atr_val:.2f}")
            st.divider()

            # --- 4. LOGIQUE DE SIMULATION (Bouton Test) ---
            if btn_backtest:
                st.subheader(f"🧪 Simulation : Entrée au Swing du {swing_date_idx.strftime('%d %b')}")
                target_ts = swing_date_idx.tz_localize(df_15.index.tz)
                hist_test = df_15[df_15.index >= target_ts]
                
                trigger = hist_test[hist_test['Low'] <= f_0618] if mode == "ACHAT (Long)" else hist_test[hist_test['High'] >= f_0618]
                
                if not trigger.empty:
                    px_entree = f_0618
                    qty = int((capital * risk_pc) / abs(px_entree - f_0786))
                    post_entry = hist_test[hist_test.index >= trigger.index[0]]
                    hit_t = post_entry[post_entry['High'] >= f_target] if mode == "ACHAT (Long)" else post_entry[post_entry['Low'] <= f_target]
                    hit_s = post_entry[post_entry['Low'] <= f_0786] if mode == "ACHAT (Long)" else post_entry[post_entry['High'] >= f_0786]
                    
                    st.info(f"📍 Entrée à {px_entree:.2f}$ (Quantité: {qty} titres)")
                    if not hit_t.empty and (hit_s.empty or hit_t.index[0] < hit_s.index[0]):
                        gain = abs(f_target - px_entree) * qty
                        st.success(f"🎯 RÉUSSITE : Gain estimé de **+{gain:,.2f} $** le {hit_t.index[0].strftime('%d %b')}")
                    elif not hit_s.empty:
                        perte = abs(px_entree - f_0786) * qty
                        st.error(f"🛑 STOP LOSS : Perte de **-{perte:,.2f} $** le {hit_s.index[0].strftime('%d %b')}")
                    else:
                        latent = (px_actuel - px_entree) * qty if mode == "ACHAT (Long)" else (px_entree - px_actuel) * qty
                        st.warning(f"⏳ EN COURS : Profit/Perte actuel : {latent:,.2f} $")
                else:
                    st.info("Le prix n'a pas encore atteint le niveau d'entrée suggéré (0.618).")

            # --- 5. PLAN DE TRADE (Bouton Analyse) ---
            elif btn_analyse:
                st.subheader("🚀 Diagnostic & Plan Stratégique")
                dist = abs(f_0618 - f_0786)
                qty = int((capital * risk_pc) / dist) if dist > 0 else 0
                gain_pc = (abs(f_target - f_0618) / f_0618) * 100
                
                cp1, cp2, cp3 = st.columns(3)
                cp1.metric("Quantité Suggérée", f"{qty} titres")
                cp2.metric("Engagement Total", f"{qty * f_0618:,.2f} $")
                cp3.metric("Profit Visé (%)", f"{gain_pc:.1f} %")

            # --- 6. GRAPHIQUE (CONSERVÉ) ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            fig.add_hrect(y0=f_0786, y1=f_05, fillcolor="rgba(0, 255, 0, 0.1)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.1)", line_width=0, row=1, col=1)
            for label, val in {"ENTRÉE": f_0618, "STOP": f_0786, "CIBLE": f_target}.items():
                fig.add_hline(y=val, line_dash="dot", annotation_text=label, annotation_position="bottom right", row=1, col=1)
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_plot['Volume']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors), row=2, col=1)
            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
