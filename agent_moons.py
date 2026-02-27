import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
st.set_page_config(page_title="Terminal Trading Expert", layout="wide")
st.title("🏦 Terminal Trading : Analyse & Anticipation")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque (%)", 0.5, 5.0, 1.0) / 100

# Création des deux boutons côte à côte
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes")

if btn_analyse or btn_anticipe:
    try:
        # Données
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Données introuvables.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS COMMUNS (Ichimoku & Fibo) ---
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            sa = ((tenkan + kijun) / 2).shift(26)
            h52, l52 = df_m['High'].rolling(52).max(), df_m['Low'].rolling(52).min()
            sb = ((h52 + l52) / 2).shift(26)
            
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            fib_05 = swing_high - (0.5 * diff)
            fib_0618 = swing_high - (0.618 * diff)
            px = df_m['Close'].iloc[-1]

            # --- CAS 1 : ANALYSE DU SIGNAL (Version Précédente) ---
            if btn_analyse:
                st.subheader(f"🔍 Analyse en temps réel : {ticker}")
                
                cond_cloud = px > max(sa.iloc[-1], sb.iloc[-1])
                cond_cross = tenkan.iloc[-1] > kijun.iloc[-1]
                cond_chikou = px > df_m['Close'].iloc[-26]
                cond_fib = fib_0618 <= px <= fib_05

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.write("**Validation Ichimoku :**")
                    st.write(f"{'✅' if cond_cloud else '❌'} Prix > Nuage")
                    st.write(f"{'✅' if cond_cross else '❌'} Tenkan > Kijun")
                    st.write(f"{'✅' if cond_chikou else '❌'} Chikou dégagée")
                with col_d2:
                    st.write("**Validation Fibonacci :**")
                    st.write(f"{'✅' if cond_fib else '❌'} Dans Golden Pocket")

                if all([cond_cloud, cond_cross, cond_chikou, cond_fib]):
                    sl = min(sa.iloc[-1], sb.iloc[-1])
                    qte = int((capital * risk_pc) / abs(px - sl))
                    tp = px + (2 * abs(px - sl))
                    st.success("🔥 SIGNAL VALIDÉ")
                    st.metric("ACHAT IMMÉDIAT", f"{px:.2f} $", f"Qte: {qte}")
                    st.info(f"🎯 Objectif (RR 1:2) : {tp:.2f} $")
                else:
                    st.warning("⚠️ Conditions non réunies pour un achat immédiat.")

            # --- CAS 2 : ANTICIPATION DES SOLDES ---
            if btn_anticipe:
                st.subheader(f"📉 Anticipation des Soldes : {ticker}")
                
                if px > fib_05:
                    entree_cible = fib_0618
                    # Stop théorique au niveau 0.786 pour l'anticipation
                    stop_prevu = swing_high - (0.786 * diff)
                    qte_prevue = int((capital * risk_pc) / abs(entree_cible - stop_prevu))
                    
                    st.info(f"L'action est haute. Préparez vos ordres pour la zone de rebond.")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("PRIX D'ENTRÉE CIBLE", f"{entree_cible:.2f} $")
                    c2.metric("STOP PRÉVU", f"{stop_prevu:.2f} $")
                    c3.metric("QUANTITÉ À PRÉPARER", f"{qte_prevue}")
                    st.write(f"🎯 *Cible de sortie (Sommet) : {swing_high:.2f} $*")
                else:
                    st.write("Le prix est déjà dans ou sous la zone de soldes. Utilisez le bouton 'Analyse' pour vérifier la force du rebond.")

            # --- GRAPHIQUE COMMUN ---
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'))
            fig.add_hrect(y0=fib_0618, y1=fib_05, fillcolor="gold", opacity=0.2, annotation_text="ZONE DE SOLDES")
            fig.add_trace(go.Scatter(x=df_m.index, y=sa, line_color='rgba(0,255,0,0.1)', name='Nuage'))
            fig.add_trace(go.Scatter(x=df_m.index, y=sb, line_color='rgba(255,0,0,0.1)', fill='tonexty', name='Nuage'))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
