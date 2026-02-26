import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Terminal Trading Pilote", layout="wide")
st.title("🏦 Terminal de Trading : Stratégie Fibonacci")

# Barre latérale pour les entrées
with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="META").upper()
    capital = st.number_input("💰 Capital total ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 5.0, 1.0) / 100

if st.button("Lancer l'Analyse"):
    try:
        df = yf.download(ticker, period="30d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="2d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Symbole introuvable.")
        else:
            # Nettoyage des colonnes si nécessaire
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # Calculs Stratégiques
            w = df.tail(15)
            sommet, base = w['High'].max(), w['Low'].min()
            amp = sommet - base
            px = df_m['Close'].iloc[-1]
            sl = (df_m['High'].rolling(26).max() + df_m['Low'].rolling(26).min()).iloc[-1] / 2

            if px <= sl:
                st.warning(f"🚨 **ATTENTE : PRIX SOUS LA KIJUN** (Prix: {px:.2f}$ | Stop: {sl:.2f}$)")
            else:
                tp1, tp2 = sommet + (0.27 * amp), sommet + (0.618 * amp)
                qte = int((capital * risk_pc) / (px - sl))
                
                # Affichage des résultats (comme ton rendu META réussi)
                c1, c2, c3 = st.columns(3)
                c1.metric("Prix d'Entrée", f"{px:.2f} $")
                c2.metric("Stop Loss", f"{sl:.2f} $")
                c3.metric("Quantité", f"{qte}")
                
                st.success(f"🎯 Vente 1 (TP1) : {tp1:.2f} $ | 🚀 Vente 2 (TP2) : {tp2:.2f} $")
                
                # Graphique interactif
                fig = make_subplots(rows=1, cols=2, column_widths=[0.7, 0.3], specs=[[{"type": "xy"}, {"type": "domain"}]])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Prix'), row=1, col=1)
                fig.add_hline(y=sl, line_dash="dash", line_color="red", row=1, col=1)
                fig.add_hline(y=tp1, line_dash="dot", line_color="cyan", row=1, col=1)
                fig.add_hline(y=tp2, line_dash="dot", line_color="gold", row=1, col=1)
                fig.update_layout(template="plotly_dark", height=450, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
