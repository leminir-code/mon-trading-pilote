import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Terminal Expert Diagnostic", layout="wide")
st.title("🏦 Terminal Expert : Diagnostic Ichimoku & Fibonacci")

with st.sidebar:
    st.header("⚙️ Paramètres")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque (%)", 0.5, 5.0, 1.0) / 100

if st.button("Lancer l'Analyse"):
    try:
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Données introuvables.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ICHIMOKU ---
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            senkou_a = ((tenkan + kijun) / 2).shift(26)
            h52, l52 = df_m['High'].rolling(52).max(), df_m['Low'].rolling(52).min()
            senkou_b = ((h52 + l52) / 2).shift(26)
            
            # --- CALCULS FIBONACCI ---
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            fib_05 = swing_high - (0.5 * diff)
            fib_0618 = swing_high - (0.618 * diff)
            
            # --- ÉTAT ACTUEL ---
            px = df_m['Close'].iloc[-1]
            last_sa, last_sb = senkou_a.iloc[-1], senkou_b.iloc[-1]
            px_past = df_m['Close'].iloc[-26] # Pour la Chikou
            
            # --- DIAGNOSTIC ICHIMOKU (Selon la vidéo) ---
            check_cloud = px > max(last_sa, last_sb)
            check_cross = tenkan.iloc[-1] > kijun.iloc[-1]
            check_chikou = px > px_past
            check_fib = fib_0618 <= px <= fib_05

            st.subheader(f"🔍 Diagnostic pour {ticker}")
            
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                st.write("**Validation Ichimoku :**")
                st.write(f"{'✅' if check_cloud else '❌'} Prix au-dessus du Nuage")
                st.write(f"{'✅' if check_cross else '❌'} Tenkan > Kijun (Momentum)")
                st.write(f"{'✅' if check_chikou else '❌'} Chikou Span dégagée (Prix passé)")

            with col_d2:
                st.write("**Validation Fibonacci :**")
                if px > fib_05:
                    st.write(f"❌ Trop cher (Prix > 0.5)")
                elif px < fib_0618:
                    st.write(f"❌ Trop bas (Structure cassée)")
                else:
                    st.write(f"✅ Dans la Golden Pocket")

            # --- RÉSULTAT FINAL ---
            if all([check_cloud, check_cross, check_chikou, check_fib]):
                stop_loss = min(last_sa, last_sb)
                qte = int((capital * risk_pc) / (px - stop_loss))
                tp = px + (2 * (px - stop_loss))
                
                st.success("🔥 SIGNAL TOTAL VALIDÉ")
                st.metric("ACHAT", f"{px:.2f} $", f"Quantité: {qte}")
                st.info(f"🎯 OBJECTIF RR 1:2 : {tp:.2f} $")
            else:
                st.warning("⚠️ Conditions non réunies : l'agent reste en attente.")

            # --- GRAPHIQUE ---
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'))
            fig.add_trace(go.Scatter(x=df_m.index, y=senkou_a, line_color='rgba(0,255,0,0.1)', name='Nuage'))
            fig.add_trace(go.Scatter(x=df_m.index, y=senkou_b, line_color='rgba(255,0,0,0.1)', fill='tonexty', name='Nuage'))
            fig.add_trace(go.Scatter(x=df_m.index, y=df_m['Close'].shift(-26), line_color='mediumpurple', name='Chikou'))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
