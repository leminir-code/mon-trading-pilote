import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Terminal Expert Ichimoku", layout="wide")
st.title("🏦 Système Expert : Golden Pocket + Ichimoku Complet")

with st.sidebar:
    st.header("⚙️ Paramètres")
    ticker = st.text_input("🔍 Symbole", value="META").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque (%)", 0.5, 5.0, 1.0) / 100

if st.button("Lancer l'Analyse"):
    try:
        # Données étendues pour les calculs de retard (Chikou) et de projection (Nuage)
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Données introuvables.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCUL ICHIMOKU COMPLET ---
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            
            senkou_a = ((tenkan + kijun) / 2).shift(26)
            h52, l52 = df_m['High'].rolling(52).max(), df_m['Low'].rolling(52).min()
            senkou_b = ((h52 + l52) / 2).shift(26)
            
            # Chikou Span : Prix de clôture décalé de 26 périodes dans le passé
            chikou = df_m['Close'].shift(-26)

            # --- CALCUL FIBONACCI ---
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            fib_05 = swing_high - (0.5 * diff)
            fib_0618 = swing_high - (0.618 * diff)
            
            # --- ÉTAT ACTUEL & VALIDATION ---
            px = df_m['Close'].iloc[-1]
            last_sa, last_sb = senkou_a.iloc[-1], senkou_b.iloc[-1]
            
            # Conditions de la vidéo
            cond_cloud = px > max(last_sa, last_sb) # Prix au-dessus du nuage
            cond_cross = tenkan.iloc[-1] > kijun.iloc[-1] # Tenkan > Kijun
            cond_chikou = px > df_m['Close'].iloc[-26] # Chikou au-dessus du prix passé
            cond_fib = fib_0618 <= px <= fib_05 # Dans la Golden Pocket

            # --- AFFICHAGE DU RÉSULTAT ---
            if not cond_cloud or not cond_cross or not cond_chikou:
                st.warning("🚨 **ICHIMOKU INVALIDE** : Les conditions de momentum ne sont pas réunies.")
                if not cond_chikou: st.write("ℹ️ *La Chikou Span est bloquée par le prix passé.*")
            elif not cond_fib:
                st.info(f"⏳ **ATTENTE ZONE FIBO** : Le prix ({px:.2f}$) n'est pas encore entre {fib_0618:.2f}$ et {fib_05:.2f}$.")
            else:
                # SIGNAL VALIDÉ
                stop_loss = min(last_sa, last_sb)
                qte = int((capital * risk_pc) / (px - stop_loss))
                tp = px + (2 * (px - stop_loss)) # Ratio 1:2
                
                st.success(f"🔥 **SIGNAL TOTAL VALIDÉ : {ticker}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("ENTRÉE", f"{px:.2f} $")
                c2.metric("STOP (Nuage)", f"{stop_loss:.2f} $")
                c3.metric("OBJECTIF (RR 1:2)", f"{tp:.2f} $")
                st.write(f"📦 **Quantité recommandée : {qte} titres**")

            # --- GRAPHIQUE TECHNIQUE ---
            fig = go.Figure()
            # Candlesticks
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'))
            # Nuage
            fig.add_trace(go.Scatter(x=df_m.index, y=senkou_a, line_color='rgba(0, 255, 0, 0.2)', name='SSA'))
            fig.add_trace(go.Scatter(x=df_m.index, y=senkou_b, line_color='rgba(255, 0, 0, 0.2)', name='SSB', fill='tonexty'))
            # Chikou Span (Violette)
            fig.add_trace(go.Scatter(x=df_m.index, y=df_m['Close'].shift(-26), line_color='mediumpurple', name='Chikou', line_width=2))
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
