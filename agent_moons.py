import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Expert Moons", layout="wide")
st.title("🏦 Terminal Expert : Stratégie & Anticipation")

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
            
            fibo = {
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "0.886": swing_high - (0.886 * diff),
                "1.618": swing_high + (0.618 * diff)
            }

            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            est_haussier = px_actuel > ma20

            # --- 1. AFFICHAGE PRIX & TENDANCE (COMMUN) ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {'green' if est_haussier else 'red'};'>Marché {'HAUSSIER 🟢' if est_haussier else 'BAISSIER 🔴'}</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. LOGIQUE DIFFÉRENCIÉE ---
            
            if btn_analyse:
                st.subheader("🚀 Analyse du Signal Immédiat")
                # Vérification si on est dans la zone Golden Pocket maintenant
                en_zone = fibo["0.786"] <= px_actuel <= fibo["0.5"]
                
                if en_zone:
                    st.success(f"🎯 SIGNAL VALIDÉ : Le prix est actuellement dans la zone de décision ({px_actuel:.2f} $).")
                else:
                    st.warning(f"⏳ ATTENTE : Le prix actuel n'est pas dans une zone d'achat optimale.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Prix Actuel", f"{px_actuel:.2f} $")
                c2.metric("Zone Entrée (0.5)", f"{fibo['0.5']:.2f} $")
                c3.metric("Plancher (0.786)", f"{fibo['0.786']:.2f} $")

            if btn_anticipe:
                st.subheader("📉 Stratégie d'Anticipation (Ordre Limite)")
                
                # Si le prix est déjà très bas (cas TSLA), on cherche un rebond plus profond
                p_cible = fibo["0.786"] if px_actuel > fibo["0.786"] else fibo["0.886"]
                
                st.info(f"💡 Planification : Ne pas acheter au prix actuel. Placer un ordre plus bas.")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Prix Cible Entrée", f"{p_cible:.2f} $", delta=f"{p_cible - px_actuel:.2f} $")
                c2.metric("Objectif Rebond", f"{swing_high:.2f} $")
                
                # Calcul Quantité pour l'anticipation
                dist_stop = abs(p_cible - swing_low)
                qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
                
                c3.metric("Risque (Perte)", f"-{(qte * dist_stop):.2f} $")
                c4.metric("Quantité à prévoir", f"{qte} titres")
                
                st.markdown(f"👉 **Action suggérée** : Placer un ordre **limite d'achat à {p_cible:.2f} $**.")

            # --- 3. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone Pastel dynamique selon le bouton
            y_high = fibo["0.5"] if btn_analyse else p_cible + (diff * 0.05)
            y_low = fibo["0.786"] if btn_analyse else p_cible - (diff * 0.05)
            
            fig.add_hrect(y0=y_low, y1=y_high, fillcolor="rgba(255, 215, 0, 0.12)", line_width=0, 
                         annotation_text="ZONE D'INTERVENTION", annotation_position="top left", row=1, col=1)
            
            # Lignes Fibo
            colors = {"0.5": "#00ff00", "0.618": "#00ced1", "0.786": "#ff4d4d", "0.886": "#ff00ff"}
            for k, v in fibo.items():
                if k in colors:
                    fig.add_hline(y=v, line_color=colors[k], annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right", row=1, col=1)

            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
