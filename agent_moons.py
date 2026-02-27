import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons : Deep Value", layout="wide")
st.title("🏦 Terminal Expert : Anticipation & Stratégie Baissière")

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
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="20d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS NIVEAUX ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].max(), df['Low'].min()
            diff = swing_high - swing_low
            
            # Définition des niveaux Fibonacci
            fibo = {
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "0.886": swing_high - (0.886 * diff),
                "1.618": swing_high + (0.618 * diff)
            }

            # Tendance via Moyenne Mobile
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            est_haussier = px_actuel > ma20
            tendance_txt = "HAUSSIER 🟢" if est_haussier else "BAISSIER 🔴"

            # --- 1. AFFICHAGE PRIX & TENDANCE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {'green' if est_haussier else 'red'};'>Marché {tendance_txt}</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. LOGIQUE D'ANTICIPATION DYNAMIQUE ---
            # Si le prix est déjà sous le 0.618 (cas de ton TSLA), on vise le 0.786 ou 0.886
            if px_actuel < fibo["0.618"]:
                p_entree_visée = fibo["0.786"] if px_actuel > fibo["0.786"] else fibo["0.886"]
                conseil = "Recherche d'un point de retournement (Deep Value)"
            else:
                p_entree_visée = fibo["0.618"]
                conseil = "Attente d'un repli standard (Soldes)"

            # --- 3. RÉCAPITULATIF STRATÉGIQUE ---
            st.write(f"### 🎯 Stratégie d'Anticipation : {conseil}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Prix Cible Entrée", f"{p_entree_visée:.2f} $", delta=f"{p_entree_visée - px_actuel:.2f} $")
            c2.metric("Plancher Critique", f"{fibo['0.886']:.2f} $")
            c3.metric("Objectif Rebond", f"{swing_high:.2f} $")
            c4.metric("Stop Invalidation", f"{swing_low:.2f} $")

            # Gestion du Risque
            dist_stop = abs(p_entree_visée - swing_low)
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            st.info(f"👉 **Plan d'entrée** : Placer un ordre limite à **{p_entree_visée:.2f} $** avec **{qte}** titres.")

            # --- 4. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone de soldes adaptée (si prix est bas, on colore la zone sous le prix actuel)
            fig.add_hrect(y0=fibo["0.886"], y1=p_entree_visée, fillcolor="rgba(255, 0, 0, 0.1)", line_width=0, annotation_text="ZONE DE REBOND ANTICIPÉE", row=1, col=1)
            
            # Niveaux Fibo
            colors = {"0.5": "gray", "0.618": "orange", "0.786": "red", "0.886": "purple", "1.618": "cyan"}
            for k, v in fibo.items():
                fig.add_hline(y=v, line_color=colors[k], annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right", row=1, col=1)

            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
