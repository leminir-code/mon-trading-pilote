import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# Configuration
st.set_page_config(page_title="Terminal Trading Expert", layout="wide")
st.title("🏦 Terminal Trading : Niveaux de Prix Réels")

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
            st.error("❌ Données introuvables.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS PRIX RÉELS ---
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            
            # Prix concrets basés sur Fibonacci
            prix_entree_suggere = swing_high - (0.5 * diff)  # Milieu de zone
            prix_chute_max = swing_high - (0.618 * diff)      # Plancher des soldes
            objectif_max_theorique = swing_high + (0.618 * diff)
            
            px_actuel = df_m['Close'].iloc[-1]

            # Affichage du Prix Réel
            st.metric(f"💰 Valeur actuelle de {ticker}", f"{px_actuel:.2f} $")

            # --- CAS 1 : ANALYSE (Signal Immédiat) ---
            if btn_analyse:
                st.subheader(f"🔍 Analyse : {ticker}")
                # Calculs Ichimoku pour validation
                h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
                tenkan = (h9 + l9) / 2
                h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
                kijun = (h26 + l26) / 2
                
                cond_fib = prix_chute_max <= px_actuel <= prix_entree_suggere
                
                if cond_fib:
                    sl = kijun.iloc[-1]
                    qte = int((capital * risk_pc) / abs(prix_entree_suggere - sl))
                    st.success("🔥 ZONE D'ACHAT VALIDÉE")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("PRIX D'ENTRÉE SUGGÉRÉ", f"{prix_entree_suggere:.2f} $")
                    c2.metric("PRIX PLANCHER (STOP)", f"{prix_chute_max:.2f} $")
                    c3.metric("OBJECTIF DE SORTIE", f"{objectif_max_theorique:.2f} $")
                else:
                    st.warning(f"Le prix actuel ({px_actuel:.2f} $) est hors zone idéale.")

            # --- CAS 2 : ANTICIPATION (Prévoir la chute) ---
            if btn_anticipe:
                st.subheader(f"📉 Anticipation de la chute : {ticker}")
                st.info(f"L'agent prévoit un repli sain. Voici les niveaux de prix à surveiller :")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("DÉBUT DES SOLDES", f"{prix_entree_suggere:.2f} $")
                c2.metric("CHUTE MAX ANTICIPÉE", f"{prix_chute_max:.2f} $", delta="Plancher", delta_color="inverse")
                c3.metric("GAIN POTENTIEL MAX", f"{objectif_max_theorique:.2f} $")
                
                st.write(f"⚠️ *Si le prix tombe sous **{prix_chute_max:.2f} $**, la tendance haussière est annulée.*")

            # --- GRAPHIQUE ---
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'))
            
            # Zones de prix réelles
            fig.add_hline(y=prix_entree_suggere, line_color="green", annotation_text=f"Entrée: {prix_entree_suggere:.2f}$")
            fig.add_hline(y=prix_chute_max, line_color="red", line_dash="dash", annotation_text=f"Plancher: {prix_chute_max:.2f}$")
            fig.add_hline(y=objectif_max_theorique, line_color="cyan", annotation_text=f"Objectif: {objectif_max_theorique:.2f}$")
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
