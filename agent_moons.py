import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Expert Moons", layout="wide")
st.title("🏦 Terminal Expert : Analyse de Tendance & Fibonacci")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 5.0, 1.0) / 100

# --- BOUTONS ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes / Hausse")

if btn_analyse or btn_anticipe:
    try:
        # Récupération des données
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].max(), df['Low'].min()
            diff = swing_high - swing_low
            
            # Niveaux Fibonacci
            levels = {
                "0 (Top)": swing_high,
                "0.236": swing_high - (0.236 * diff),
                "0.382": swing_high - (0.382 * diff),
                "0.5 (Entrée)": swing_high - (0.5 * diff),
                "0.618 (Plancher)": swing_high - (0.618 * diff),
                "0.786 (Stop)": swing_high - (0.786 * diff),
                "1 (Bottom)": swing_low,
                "1.618 (Objectif)": swing_high + (0.618 * diff)
            }

            # --- DÉTERMINATION DE LA TENDANCE (Moyenne Mobile 20 jours) ---
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            tendance = "HAUSSIER 🟢" if px_actuel > ma20 else "BAISSIER 🔴"
            couleur_tendance = "green" if px_actuel > ma20 else "red"

            # --- 1. AFFICHAGE PRIORITAIRE (PRIX & TENDANCE) ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {couleur_tendance};'>Marché {tendance}</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. RÉCAPITULATIF DES PRIX & GESTION DU RISQUE ---
            st.markdown(f"### 📝 Niveaux de Prix & Gestion du Risque")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Entrée 0.5", f"{levels['0.5 (Entrée)']:.2f} $")
            c2.metric("Plancher 0.618", f"{levels['0.618 (Plancher)']:.2f} $")
            c3.metric("Objectif 1.618", f"{levels['1.618 (Objectif)']:.2f} $")
            c4.metric("Stop 0.786", f"{levels['0.786 (Stop)']:.2f} $")

            dist_stop = abs(levels['0.5 (Entrée)'] - levels['0.786 (Stop)'])
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            perte = qte * dist_stop
            gain = qte * abs(levels['1.618 (Objectif)'] - levels['0.5 (Entrée)'])
            
            cg1, cg2, cg3 = st.columns(3)
            cg1.metric("🔴 Risque (Perte Max)", f"-{perte:.2f} $")
            cg2.metric("🟢 Potentiel (Gain Max)", f"+{gain:.2f} $")
            cg3.metric("📦 Quantité suggérée", f"{qte} titres")
            st.divider()

            # --- 3. GRAPHIQUE STYLE TRADINGVIEW ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone Pastel
            fig.add_hrect(y0=levels["0.618 (Plancher)"], y1=levels["0.5 (Entrée)"], fillcolor="rgba(255, 215, 0, 0.12)", line_width=0, annotation_text="ZONE DE SOLDES", annotation_position="top left", row=1, col=1)
            
            # Lignes Fibonacci
            colors = {"0 (Top)": "gray", "0.236": "#ff4d4d", "0.382": "#ffa500", "0.5 (Entrée)": "#00ff00", "0.618 (Plancher)": "#00ced1", "0.786 (Stop)": "#1e90ff", "1 (Bottom)": "white", "1.618 (Objectif)": "#ff00ff"}
            for label, val in levels.items():
                fig.add_hline(y=val, line_color=colors.get(label, "white"), annotation_text=f"{label} ({val:.2f}$)", annotation_position="bottom right", row=1, col=1)

            # Volume
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], marker_color=v_colors, opacity=0.8), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
