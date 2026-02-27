import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Expert", layout="wide")
st.title("🏦 Terminal Expert : Stratégie Ichimoku & Fibonacci")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 5.0, 1.0) / 100

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes / Hausse")

if btn_analyse or btn_anticipe:
    try:
        # Récupération des données (60 jours pour trouver un vrai Swing)
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- PRIX ACTUEL (AFFICHAGE PRIORITAIRE) ---
            px_actuel = df_m['Close'].iloc[-1]
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.divider()

            # --- CALCULS FIBONACCI (Recherche d'un vrai mouvement) ---
            # On cherche le point haut et bas sur les 60 derniers jours pour éviter que prix actuel = sommet
            swing_high = df['High'].max()
            swing_low = df['Low'].min()
            diff = swing_high - swing_low
            
            levels = {
                "0 (Sommet)": swing_high,
                "0.5 (Entrée)": swing_high - (0.5 * diff),
                "0.618 (Soldes)": swing_high - (0.618 * diff),
                "0.786 (Stop)": swing_high - (0.786 * diff),
                "1.272 (Objectif)": swing_high + (0.272 * diff)
            }

            # --- CALCULS ICHIMOKU ---
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            sa = ((tenkan + kijun) / 2).shift(26)
            sb = ((df_m['High'].rolling(52).max() + df_m['Low'].rolling(52).min()) / 2).shift(26)

            # --- 1. RÉCAPITULATIF DES PRIX ---
            st.write("### 📝 Niveaux Stratégiques (Basés sur le cycle actuel)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Entrée (0.5)", f"{levels['0.5 (Entrée)']:.2f} $")
            c2.metric("Soldes (0.618)", f"{levels['0.618 (Soldes)']:.2f} $")
            c3.metric("Objectif (1.272)", f"{levels['1.272 (Objectif)']:.2f} $")
            c4.metric("Stop (0.786)", f"{levels['0.786 (Stop)']:.2f} $")

            # --- 2. GESTION DU RISQUE ---
            dist_stop = abs(levels['0.5 (Entrée)'] - levels['0.786 (Stop)'])
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            gain_pot = qte * abs(levels['1.272 (Objectif)'] - levels['0.5 (Entrée)'])
            
            st.write("### 🧮 Calculateur Gain/Perte")
            cg1, cg2, cg3 = st.columns(3)
            cg1.metric("🔴 Risque (Perte)", f"-{(qte * dist_stop):.2f} $")
            cg2.metric("🟢 Potentiel (Gain)", f"+{gain_pot:.2f} $")
            cg3.metric("📦 Quantité", f"{qte} titres")

            # --- 3. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Ichimoku Cloud
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line_color='rgba(0, 255, 0, 0.1)', name='Cloud A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line_color='rgba(255, 0, 0, 0.1)', fill='tonexty', name='Cloud B'), row=1, col=1)

            # Zone Pastel (Soldes) - Étiquette à gauche
            fig.add_hrect(y0=levels["0.618 (Soldes)"], y1=levels["0.5 (Entrée)"], fillcolor="rgba(255, 215, 0, 0.12)", line_width=0, annotation_text="ZONE DE SOLDES", annotation_position="top left", row=1, col=1)
            
            # Lignes Fibonacci TradingView - Prix à droite
            colors = {"0 (Sommet)": "gray", "0.5 (Entrée)": "#00ff00", "0.618 (Soldes)": "#00ced1", "0.786 (Stop)": "#ff4d4d", "1.272 (Objectif)": "#ff00ff"}
            for label, val in levels.items():
                fig.add_hline(y=val, line_color=colors.get(label, "white"), annotation_text=f"{label} ({val:.2f}$)", annotation_position="bottom right", row=1, col=1)

            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
