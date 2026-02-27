import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Dynamique", layout="wide")
st.title("🏦 Terminal Expert : Calibration Dynamique & Phases")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 5.0, 1.0) / 100
    
    st.divider()
    # NOUVEAU : Calibration dynamique de la période de calcul
    st.subheader("📏 Calibration Dynamique")
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)
    st.info(f"Analyse basée sur les {lookback} derniers jours.")

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes / Hausse")

if btn_analyse or btn_anticipe:
    try:
        # 1. RÉCUPÉRATION DYNAMIQUE (Utilise la variable 'lookback')
        df = yf.download(ticker, period=f"{lookback + 10}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS BASÉS SUR LA CALIBRATION ---
            df_lookback = df.tail(lookback)
            swing_high = df_lookback['High'].max()
            swing_low = df_lookback['Low'].min()
            diff = swing_high - swing_low
            
            px_actuel = df_m['Close'].iloc[-1]
            
            fibo = {
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "0.886": swing_high - (0.886 * diff)
            }

            # 2. DÉTECTION DE LA PHASE DE CONSOLIDATION (Dynamique)
            # On considère une consolidation si le range est < 5% sur 1/3 de la période choisie
            check_range = max(int(lookback/3), 5)
            recent_range = (df['High'].tail(check_range).max() - df['Low'].tail(check_range).min()) / df['Low'].tail(check_range).min() * 100
            est_en_consolidation = recent_range < 5.0
            phase_txt = "CONSOLIDATION 🟦" if est_en_consolidation else "IMPULSION 🚀"

            # --- 1. AFFICHAGE PRIX & PHASE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center;'>Phase ({lookback}j) : {phase_txt}</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. LOGIQUE SELON LE BOUTON ---
            if btn_analyse:
                st.subheader("🚀 Analyse du Signal")
                if est_en_consolidation:
                    st.warning(f"⚠️ Marché latéral sur les {check_range} derniers jours. Attendez une cassure.")
                
                en_zone = fibo["0.786"] <= px_actuel <= fibo["0.5"]
                if en_zone:
                    st.success(f"🎯 SIGNAL DÉTECTÉ : Prix dans la zone de décision ({px_actuel:.2f} $).")
                else:
                    st.info("Le prix est actuellement hors de la zone d'achat optimale.")

            if btn_anticipe:
                st.subheader("📉 Plan d'Anticipation Dynamique")
                # Gestion Deep Value si déjà sous 0.618
                p_cible = fibo["0.786"] if px_actuel > fibo["0.786"] else fibo["0.886"]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Prix Cible Entrée", f"{p_cible:.2f} $", delta=f"{p_cible - px_actuel:.2f} $")
                
                dist_stop = abs(p_cible - swing_low)
                qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
                
                c2.metric("Risque (Perte)", f"-{(qte * dist_stop):.2f} $")
                c3.metric("Quantité suggérée", f"{qte} titres")

            # --- 3. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone Pastel
            y_top = fibo["0.5"] if btn_analyse else p_cible + (diff * 0.02)
            y_bot = fibo["0.786"] if btn_analyse else p_cible - (diff * 0.02)
            fig.add_hrect(y0=y_bot, y1=y_top, fillcolor="rgba(255, 215, 0, 0.12)", line_width=0, annotation_text="ZONE D'ACTION", row=1, col=1)
            
            # Lignes Fibonacci
            for k, v in fibo.items():
                fig.add_hline(y=v, line_color="rgba(255, 255, 255, 0.3)", annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right", row=1, col=1)

            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
