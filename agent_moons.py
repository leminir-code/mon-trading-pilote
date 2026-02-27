import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
st.set_page_config(page_title="Terminal Trading Expert + Volume", layout="wide")
st.title("🏦 Terminal Trading : Intelligence Prédictive & Volume")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="MSI").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque (%)", 0.5, 5.0, 1.0) / 100

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes")

if btn_analyse or btn_anticipe:
    try:
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Données indisponibles.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS PRIX ---
            swing_high, swing_low = df['High'].tail(30).max(), df['Low'].tail(30).min()
            diff = swing_high - swing_low
            p_entree, p_chute_max = swing_high - (0.5 * diff), swing_high - (0.618 * diff)
            obj_max = swing_high + (0.618 * diff)
            px_actuel = df_m['Close'].iloc[-1]
            
            # --- ANALYSE DU VOLUME ---
            vol_actuel = df_m['Volume'].iloc[-1]
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            ratio_vol = vol_actuel / vol_moyen

            # --- SÉMANTIQUE TENDANCE ---
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26).iloc[-1] / 2
            titre = "Anticipation de hausse" if px_actuel > kijun else "Anticipation de croissance"

            # --- AFFICHAGE ALERTE VISUELLE DU VOLUME ---
            st.subheader("📊 État du Marché")
            if ratio_vol >= 1.5:
                st.success(f"💎 **VOLUME EXPLOSIF ({ratio_vol:.1f}x la moyenne)** : Les institutions achètent massivement. Le signal est très fiable.")
            elif ratio_vol >= 1.1:
                st.info(f"✅ **VOLUME CONFIRMÉ ({ratio_vol:.1f}x la moyenne)** : Il y a assez d'activité pour soutenir le mouvement.")
            else:
                st.warning(f"⚠️ **VOLUME FAIBLE ({ratio_vol:.1f}x la moyenne)** : Attention, le mouvement manque de conviction. Risque de faux rebond.")

            if btn_analyse:
                st.subheader(f"🔍 Analyse : {ticker}")
                if p_chute_max <= px_actuel <= p_entree:
                    st.success(f"🔥 {titre.upper()} VALIDÉE")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRÉE SUGGÉRÉE", f"{p_entree:.2f} $")
                    c2.metric("CHUTE MAX (PLANCHER)", f"{p_chute_max:.2f} $")
                    c3.metric("CIBLE FINALE", f"{obj_max:.2f} $")
                else:
                    st.warning(f"Prix hors zone idéale ({px_actuel:.2f} $).")

            if btn_anticipe:
                st.subheader(f"📉 {titre} : {ticker}")
                c1, c2, c3 = st.columns(3)
                c1.metric("DÉBUT DES SOLDES", f"{p_entree:.2f} $")
                c2.metric("CHUTE MAX ANTICIPÉE", f"{p_chute_max:.2f} $")
                c3.metric("POTENTIEL DE GAIN", f"{obj_max:.2f} $")

            # --- GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            # Volume coloré : vert si vol > moyenne, rouge sinon
            colors = ['#00FF00' if v > vol_moyen else '#FF0000' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], name='Volume', marker_color=colors), row=2, col=1)
            
            fig.add_hline(y=p_entree, line_color="green", row=1, col=1)
            fig.add_hline(y=p_chute_max, line_color="red", line_dash="dash", row=1, col=1)
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
