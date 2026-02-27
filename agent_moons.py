import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Dynamique", layout="wide")
st.title("🏦 Terminal Expert : Gestion du Risque & Objectifs Max")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    # NOUVEAU : Risque Dynamique
    st.subheader("⚠️ Gestion du Risque")
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    
    # Calibration de la fenêtre
    st.subheader("📏 Calibration")
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes / Hausse")

if btn_analyse or btn_anticipe:
    try:
        # Récupération des données
        df = yf.download(ticker, period=f"{lookback+10}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="5d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- PRIX TEMPS RÉEL ---
            px_actuel = df_m['Close'].iloc[-1]
            
            # --- CALCULS FIBONACCI ---
            df_snap = df.tail(lookback)
            swing_high, swing_low = df_snap['High'].max(), df_snap['Low'].min()
            diff = swing_high - swing_low
            
            fibo = {
                "0.5 (Entrée)": swing_high - (0.5 * diff),
                "0.618 (Soldes)": swing_high - (0.618 * diff),
                "0.786 (Stop)": swing_high - (0.786 * diff),
                "1.618 (OBJECTIF MAX)": swing_high + (0.618 * diff)
            }

            # --- 1. AFFICHAGE PRIX TEMPS RÉEL ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $ (Live)</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: #00FF00;'>Hausse Max Visée : {fibo['1.618 (OBJECTIF MAX)']:.2f} $</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. CALCULATEUR DE RISQUE DYNAMIQUE ---
            dist_stop = abs(fibo["0.5 (Entrée)"] - fibo["0.786 (Stop)"])
            montant_risque_dollar = capital * risk_pc
            qte = int(montant_risque_dollar / dist_stop) if dist_stop > 0 else 0
            
            perte_max = qte * dist_stop
            gain_max = qte * (fibo["1.618 (OBJECTIF MAX)"] - fibo["0.5 (Entrée)"])

            st.write(f"### 🧮 Analyse du Risque ({risk_pc*100:.1f}%)")
            c1, c2, c3 = st.columns(3)
            c1.metric("🔴 Perte si Stop", f"-{perte_max:.2f} $")
            c2.metric("🟢 Gain si Objectif", f"+{gain_max:.2f} $")
            c3.metric("📦 Quantité", f"{qte} titres")

            # --- 3. GRAPHIQUE AVEC ZONE À GAUCHE ---
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix Live'))
            
            # ZONE À GAUCHE
            fig.add_hrect(
                y0=fibo["0.786 (Stop)"], y1=fibo["0.5 (Entrée)"], 
                fillcolor="rgba(255, 215, 0, 0.12)", line_width=0, 
                annotation_text="ZONE D'ACHAT", annotation_position="top left"
            )
            
            # LIGNES DE PRIX À DROITE
            colors = {"0.5 (Entrée)": "#00FF00", "0.618 (Soldes)": "#00CED1", "0.786 (Stop)": "#FF4D4D", "1.618 (OBJECTIF MAX)": "#FF00FF"}
            for label, val in fibo.items():
                fig.add_hline(y=val, line_color=colors.get(label, "white"), annotation_text=f"{label} : {val:.2f}$", annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
