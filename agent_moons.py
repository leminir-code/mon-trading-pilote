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
    ticker = st.text_input("🔍 Symbole", value="MSI").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque (%)", 0.5, 5.0, 1.0) / 100

# Boutons
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper les Soldes")

if btn_analyse or btn_anticipe:
    try:
        # Récupération des données
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Données introuvables.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ---
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            sa = ((tenkan + kijun) / 2).shift(26)
            sb = ((df_m['High'].rolling(52).max() + df_m['Low'].rolling(52).min()) / 2).shift(26)
            
            # Fibonacci
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            fib_05 = swing_high - (0.5 * diff)
            fib_0618 = swing_high - (0.618 * diff)
            
            # --- NOUVEAU : OBJECTIF MAXIMUM (Extension 1.618) ---
            objectif_max = swing_high + (0.618 * diff)
            
            # --- PRIX EN TEMPS RÉEL ---
            px_actuel = df_m['Close'].iloc[-1]

            # Affichage du prix actuel en évidence
            st.metric(f"📈 Prix en temps réel ({ticker})", f"{px_actuel:.2f} $")

            # --- CAS 1 : ANALYSE DU SIGNAL ---
            if btn_analyse:
                st.subheader(f"🔍 Analyse : {ticker}")
                
                cond_cloud = px_actuel > max(sa.iloc[-1], sb.iloc[-1])
                cond_cross = tenkan.iloc[-1] > kijun.iloc[-1]
                cond_chikou = px_actuel > df_m['Close'].iloc[-26]
                cond_fib = fib_0618 <= px_actuel <= fib_05

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.write("**Ichimoku :**")
                    st.write(f"{'✅' if cond_cloud else '❌'} Prix > Nuage")
                    st.write(f"{'✅' if cond_cross else '❌'} Tenkan > Kijun")
                    st.write(f"{'✅' if cond_chikou else '❌'} Chikou dégagée")
                with col_d2:
                    st.write("**Fibonacci :**")
                    st.write(f"{'✅' if cond_fib else '❌'} Dans Golden Pocket")

                if all([cond_cloud, cond_cross, cond_chikou, cond_fib]):
                    sl = min(sa.iloc[-1], sb.iloc[-1])
                    prix_suggere = fib_05 
                    qte = int((capital * risk_pc) / abs(prix_suggere - sl))
                    
                    st.success("🔥 SIGNAL VALIDÉ")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRÉE (0.5)", f"{prix_suggere:.2f} $")
                    c2.metric("STOP LOSS", f"{sl:.2f} $")
                    c3.metric("QUANTITÉ", f"{qte}")
                    st.info(f"🚀 **OBJECTIF MAX THÉORIQUE : {objectif_max:.2f} $**")
                else:
                    st.warning("⚠️ Conditions non réunies pour un achat immédiat.")

            # --- CAS 2 : ANTICIPATION ---
            if btn_anticipe:
                st.subheader(f"📉 Anticipation : {ticker}")
                if px_actuel > fib_05:
                    entree_cible = fib_0618
                    stop_prevu = swing_high - (0.786 * diff)
                    qte_prevue = int((capital * risk_pc) / abs(entree_cible - stop_prevu))
                    
                    st.info(f"L'action est haute. Surveillez le retour vers les soldes.")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ENTRÉE CIBLE (0.618)", f"{entree_cible:.2f} $")
                    c2.metric("OBJECTIF MAX PRÉVU", f"{objectif_max:.2f} $")
                    c3.metric("QUANTITÉ À PRÉPARER", f"{qte_prevue}")
                else:
                    st.write(f"Prix actuel : {px_actuel:.2f} $. Déjà proche des soldes.")

            # --- GRAPHIQUE ---
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'))
            fig.add_hrect(y0=fib_0618, y1=fib_05, fillcolor="gold", opacity=0.2, annotation_text="ZONE DE SOLDES")
            
            # Lignes d'objectifs sur le graphique
            fig.add_hline(y=objectif_max, line_dash="dash", line_color="cyan", annotation_text="OBJ. MAX (1.618)")
            fig.add_hline(y=px_actuel, line_color="white", opacity=0.5, annotation_text="PRIX ACTUEL")
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
