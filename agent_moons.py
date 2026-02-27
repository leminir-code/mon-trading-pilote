import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons : Risk Management", layout="wide")
st.title("🏦 Terminal Expert : Gestion du Risque (Gain/Perte)")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="AAPL").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 5.0, 1.0) / 100

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes / Hausses")

if btn_analyse or btn_anticipe:
    try:
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS FIBONACCI ---
            swing_high, swing_low = df['High'].tail(30).max(), df['Low'].tail(30).min()
            diff = swing_high - swing_low
            
            levels = {
                "0 (Top)": swing_high,
                "0.5 (Entrée)": swing_high - (0.5 * diff),
                "0.618 (Plancher)": swing_high - (0.618 * diff),
                "0.786 (Stop)": swing_high - (0.786 * diff),
                "1.618 (Objectif)": swing_high + (0.618 * diff)
            }
            px_actuel = df_m['Close'].iloc[-1]

            # --- 1. RÉCAPITULATIF DES PRIX ---
            st.write(f"### 📝 Niveaux de Prix : {ticker}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Entrée (0.5)", f"{levels['0.5 (Entrée)']:.2f} $")
            c2.metric("Plancher (0.618)", f"{levels['0.618 (Plancher)']:.2f} $")
            c3.metric("Objectif (1.618)", f"{levels['1.618 (Objectif)']:.2f} $")
            c4.metric("Stop (0.786)", f"{levels['0.786 (Stop)']:.2f} $")

            # --- 2. CALCULATEUR GAIN / PERTE (NOUVEAU) ---
            st.write("### 🧮 Calculateur de Risque & Rendement")
            
            # Calcul de la quantité d'actions basée sur le risque (Stop 0.786)
            distance_stop = abs(levels['0.5 (Entrée)'] - levels['0.786 (Stop)'])
            montant_risque = capital * risk_pc
            qte = int(montant_risque / distance_stop) if distance_stop > 0 else 0
            
            # Calcul Gain/Perte
            perte_totale = qte * distance_stop
            gain_total = qte * abs(levels['1.618 (Objectif)'] - levels['0.5 (Entrée)'])
            ratio_rr = gain_total / perte_totale if perte_totale > 0 else 0

            col_g1, col_g2, col_g3 = st.columns(3)
            col_g1.metric("🔴 Perte si Stop touché", f"-{perte_totale:.2f} $", delta_color="inverse")
            col_g2.metric("🟢 Gain si Objectif atteint", f"+{gain_total:.2f} $")
            col_g3.metric("⚖️ Ratio Risk/Reward", f"1 : {ratio_rr:.2f}")

            st.write(f"👉 *Pour ce trade, achetez **{qte}** actions à **{levels['0.5 (Entrée)']:.2f} $**.*")

            # --- 3. DIAGNOSTICS ---
            vol_actuel, vol_moyen = df_m['Volume'].iloc[-1], df_m['Volume'].rolling(20).mean().iloc[-1]
            if vol_actuel > vol_moyen * 1.5:
                st.success(f"💎 VOLUME EXPLOSIF : Confirmation de force.")
            
            # --- 4. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone de Soldes
            fig.add_hrect(y0=levels["0.618 (Plancher)"], y1=levels["0.5 (Entrée)"], fillcolor="rgba(255, 215, 0, 0.15)", line_width=0, annotation_text="ZONE D'ACHAT", row=1, col=1)
            
            colors = {"0 (Top)": "gray", "0.5 (Entrée)": "#00ff00", "0.618 (Plancher)": "#00ced1", "0.786 (Stop)": "#ff4d4d", "1.618 (Objectif)": "#ff00ff"}
            for label, val in levels.items():
                fig.add_hline(y=val, line_color=colors.get(label, "white"), annotation_text=f"{label} ({val:.2f}$)", annotation_position="bottom right", row=1, col=1)

            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
