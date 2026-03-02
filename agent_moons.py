import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Terminal Moons Intelligence Totale", layout="wide")
st.title("🏦 Terminal Expert : Stratégie, Risque & Simulation")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="MSI").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)

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

# --- BOUTONS D'ACTION ---
col_btn1, col_btn2, col_btn3 = st.columns(3)
btn_analyse = col_btn1.button("🚀 Analyser la Confluence")
btn_anticipe = col_btn2.button("📈 Plan de Trade & Risque")
btn_backtest = col_btn3.button("🧪 Lancer l'Essai (30j)")

if btn_analyse or btn_anticipe or btn_backtest:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]

            # --- 1. SMART SWING & FIBONACCI ---
            df_recent = df_d.tail(lookback)
            swing_point = df_recent['High'].max() if mode == "ACHAT (Long)" else df_recent['Low'].min()
            swing_date = df_recent['High'].idxmax().strftime('%Y-%m-%d') if mode == "ACHAT (Long)" else df_recent['Low'].idxmin().strftime('%Y-%m-%d')
            base_ref = df_recent['Low'].min() if mode == "ACHAT (Long)" else df_recent['High'].max()
            diff = abs(swing_point - base_ref)
            
            f_05 = swing_point - (0.5 * diff) if mode == "ACHAT (Long)" else swing_point + (0.5 * diff)
            f_0618 = swing_point - (0.618 * diff) if mode == "ACHAT (Long)" else swing_point + (0.618 * diff)
            f_0786 = swing_point - (0.786 * diff) if mode == "ACHAT (Long)" else swing_point + (0.786 * diff)
            f_target = swing_point + (0.618 * diff) if mode == "ACHAT (Long)" else swing_point - (0.618 * diff)

            # --- 2. SCORES, VOLUME & ATR ---
            score_d, _, _, _, _ = get_ichimoku_score(df_d, mode)
            score_15, tk_15, kj_15, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            
            vol_actuel = df_15['Volume'].iloc[-1]
            vol_moyen = df_15['Volume'].rolling(20).mean().iloc[-1]
            ratio_vol = vol_actuel / vol_moyen
            
            atr_series = calculate_atr(df_15)
            atr_val = atr_series.iloc[-1]
            atr_status = "DANGER 🔴" if atr_val > atr_series.tail(100).mean() * 1.5 else "STABLE ✅"

            # --- 3. AFFICHAGE DES MÉTRIQUES ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date du Pivot", swing_date, f"{swing_point:.2f} $")
            c2.metric("Scores (D|15m)", f"{score_d}/4 | {score_15}/4")
            c3.metric("Intensité Volume", f"{ratio_vol:.2f}x")
            c4.metric("Volatilité ATR", f"{atr_val:.2f}", delta=atr_status)
            st.divider()

            # --- LOGIQUE DES BOUTONS ---
            if btn_backtest:
                st.subheader("🧪 Résultats de l'essai (30 jours)")
                hist_30 = df_15.tail(30 * 96)
                success = hist_30[hist_30['High'] >= f_target].shape[0] if mode == "ACHAT (Long)" else hist_30[hist_30['Low'] <= f_target].shape[0]
                fails = hist_30[hist_30['Low'] <= f_0786].shape[0] if mode == "ACHAT (Long)" else hist_30[hist_30['High'] >= f_0786].shape[0]
                
                cb1, cb2 = st.columns(2)
                cb1.metric("Réussites (Objectif)", f"{success}")
                cb2.metric("Échecs (Stop Loss)", f"{fails}")
                if success > fails: st.success("✅ Stratégie statistiquement profitable sur ce titre récemment.")
                else: st.warning("⚠️ Prudence : Le titre invalide souvent ses zones actuellement.")

            elif btn_analyse:
                st.subheader("🚀 Diagnostic de Confluence")
                en_zone = min(f_05, f_0786) <= px_actuel <= max(f_05, f_0786)
                if en_zone and ratio_vol >= 0.8: st.success("🎯 CONFLUENCE : Prix en zone avec volume validé.")
                else: st.info("🔭 Observation : En attente de confluence optimale.")

            elif btn_anticipe:
                st.subheader("📈 Plan de Trade & Risque")
                recommandation = f_0786 if (mode == "ACHAT (Long)" and px_actuel < f_0618) else f_0618
                dist = abs(recommandation - f_0786)
                qty = int((capital * risk_pc) / dist) if dist > 0 else 0
                
                cp1, cp2, cp3 = st.columns(3)
                cp1.metric("Quantité suggérée", f"{qty} titres")
                cp2.metric("Engagement", f"{qty * recommandation:,.2f} $")
                cp3.metric("Profit Visé (%)", f"{((abs(f_target - recommandation)/recommandation)*100):.1f} %")

            # --- 4. GRAPHIQUE COMPLET ---
            df_plot = df_15.tail(500)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            
            color_z = "rgba(0, 255, 0, 0.12)" if mode == "ACHAT (Long)" else "rgba(255, 0, 0, 0.12)"
            fig.add_hrect(y0=f_0786, y1=f_05, fillcolor=color_z, line_width=0, annotation_text="ZONE ACTION", annotation_position="top left", row=1, col=1)
            
            for label, val in {"0.618": f_0618, "0.786": f_0786, "OBJ 1.618": f_target}.items():
                fig.add_hline(y=val, line_dash="dot", line_color="rgba(255,255,255,0.3)", annotation_text=f"{label}: {val:.2f}$", annotation_position="bottom right", row=1, col=1)

            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_plot['Volume']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
