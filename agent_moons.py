import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Strategy Tester", layout="wide")
st.title("🏦 Terminal Expert : Simulation & Backtest 30j")

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

# --- BOUTONS D'ACTION ---
col_btn1, col_btn2, col_btn3 = st.columns(3)
btn_analyse = col_btn1.button("🚀 Analyser")
btn_anticipe = col_btn2.button("📈 Plan de Trade")
btn_backtest = col_btn3.button("🧪 Lancer l'Essai (30j)")

if btn_analyse or btn_anticipe or btn_backtest:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]

            # --- CALCULS FIBO ACTUELS ---
            df_recent = df_d.tail(lookback)
            swing_h, swing_l = df_recent['High'].max(), df_recent['Low'].min()
            diff = swing_h - swing_l
            
            if mode == "ACHAT (Long)":
                entree, stop, target = swing_h - (0.618 * diff), swing_h - (0.786 * diff), swing_h + (0.618 * diff)
            else:
                entree, stop, target = swing_l + (0.618 * diff), swing_l + (0.786 * diff), swing_l - (0.618 * diff)

            # --- AFFICHAGE MÉTRIQUES ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            # --- MODULE BACKTEST (NOUVEAU) ---
            if btn_backtest:
                st.subheader("🧪 Résultats de l'essai sur les 30 derniers jours")
                hist_30 = df_15.tail(30 * 96) # Approx 30 jours en 15min
                
                # Simulation simplifiée
                touch_entree = hist_30[hist_30['Low'] <= entree] if mode == "ACHAT" else hist_30[hist_30['High'] >= entree]
                
                if not touch_entree.empty:
                    success = hist_30[hist_30['High'] >= target].shape[0] if mode == "ACHAT" else hist_30[hist_30['Low'] <= target].shape[0]
                    fails = hist_30[hist_30['Low'] <= stop].shape[0] if mode == "ACHAT" else hist_30[hist_30['High'] >= stop].shape[0]
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Signaux détectés", "Oui", delta="En zone")
                    c2.metric("Tests Objectif", f"{success}", delta="Réussites", delta_color="normal")
                    c3.metric("Tests Stop Loss", f"{fails}", delta="Échecs", delta_color="inverse")
                    
                    if success > fails:
                        st.success(f"✅ Essai concluant : La structure de {ticker} respecte bien les paliers Fibonacci actuellement.")
                    else:
                        st.warning(f"⚠️ Prudence : Le titre a touché son stop plus souvent que son objectif sur 30 jours.")
                else:
                    st.info("Aucune entrée en zone détectée sur les 30 derniers jours pour ce swing.")

            # --- PLAN DE TRADE ---
            if btn_anticipe:
                st.subheader("📉 Plan Stratégique")
                risque_dollar = capital * risk_pc
                dist = abs(entree - stop)
                qty = int(risque_dollar / dist) if dist > 0 else 0
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Quantité (Essai)", f"{qty} titres")
                col_b.metric("Entrée Idéale", f"{entree:.2f} $")
                col_c.metric("Profit Visé (%)", f"{((abs(target-entree)/entree)*100):.1f} %")

            # --- GRAPHIQUE ---
            df_plot = df_15.tail(500)
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'))
            
            # Niveaux visuels
            colors = ["#00FF00", "#FF0000", "#FFFF00"]
            for val, label, clr in zip([entree, stop, target], ["ENTRÉE", "STOP", "CIBLE"], colors):
                fig.add_hline(y=val, line_dash="dot", line_color=clr, annotation_text=label)

            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur lors de l'essai : {e}")
