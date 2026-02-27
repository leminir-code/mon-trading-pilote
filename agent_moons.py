import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons : Décision", layout="wide")
st.title("🏦 Terminal Expert : Signaux d'Achat & de Vente")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    st.subheader("⚠️ Gestion du Risque")
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    
    st.subheader("📏 Calibration")
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 90, 30)

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper : Acheter ou Vendre")

if btn_analyse or btn_anticipe:
    try:
        df = yf.download(ticker, period=f"{lookback+10}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="5d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- DONNÉES ---
            px_actuel = df_m['Close'].iloc[-1]
            df_snap = df.tail(lookback)
            swing_high, swing_low = df_snap['High'].max(), df_snap['Low'].min()
            diff = swing_high - swing_low
            
            fibo = {
                "0.5 (Entrée)": swing_high - (0.5 * diff),
                "0.618 (Soldes)": swing_high - (0.618 * diff),
                "0.786 (Stop)": swing_high - (0.786 * diff),
                "1.618 (OBJ. MAX)": swing_high + (0.618 * diff)
            }

            # --- AFFICHAGE PRIX LIVE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.divider()

            # --- LOGIQUE ANTICIPATION (ACHAT/VENTE) ---
            if btn_anticipe:
                st.subheader("📉 Diagnostic d'Anticipation")
                
                # Cas 1 : Vendre (Prix proche ou au-dessus de l'objectif Max)
                if px_actuel >= fibo["1.618 (OBJ. MAX)"] * 0.98: # Marge de 2%
                    st.error(f"🚨 ALERTE VENTE : Le titre a atteint le retracement maximum ({fibo['1.618 (OBJ. MAX)']:.2f} $). Prenez vos profits !")
                    st.balloons()
                
                # Cas 2 : Acheter (Prix dans ou proche de la zone de soldes)
                elif px_actuel <= fibo["0.5 (Entrée)"] and px_actuel >= fibo["0.786 (Stop)"]:
                    st.success(f"🛒 C'EST LES SOLDES : Le prix est idéal pour un achat ({px_actuel:.2f} $).")
                
                # Cas 3 : Attente
                else:
                    st.info("⌛ AUCUN SIGNAL : Le prix est entre deux zones. Attendez un retour aux soldes ou une extension max.")

                # Récap des montants
                c1, c2, c3 = st.columns(3)
                c1.metric("Acheter aux Soldes", f"{fibo['0.618 (Soldes)']:.2f} $")
                c2.metric("Vendre à l'Objectif", f"{fibo['1.618 (OBJ. MAX)']:.2f} $")
                
                dist_stop = abs(fibo["0.618 (Soldes)"] - fibo["0.786 (Stop)"])
                qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
                c3.metric("Quantité suggérée", f"{qte} titres")

            if btn_analyse:
                st.subheader("🚀 Analyse Technique Immédiate")
                st.write(f"Prix actuel comparé au point pivot 0.5 : {px_actuel:.2f} $ vs {fibo['0.5 (Entrée)']:.2f} $")

            # --- GRAPHIQUE (Zone à gauche, Prix à droite) ---
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Live'))
            
            # Zone d'Achat (Soldes)
            fig.add_hrect(y0=fibo["0.786 (Stop)"], y1=fibo["0.5 (Entrée)"], fillcolor="rgba(0, 255, 0, 0.1)", line_width=0, annotation_text="ZONE SOLDES", annotation_position="top left")
            
            # Zone de Vente (Profit Max)
            fig.add_hrect(y0=fibo["1.618 (OBJ. MAX)"] * 0.95, y1=fibo["1.618 (OBJ. MAX)"] * 1.05, fillcolor="rgba(255, 0, 0, 0.1)", line_width=0, annotation_text="ZONE VENTE MAX", annotation_position="top left")
            
            colors = {"0.5 (Entrée)": "#00FF00", "0.618 (Soldes)": "#00CED1", "0.786 (Stop)": "#FF4D4D", "1.618 (OBJ. MAX)": "#FF00FF"}
            for label, val in fibo.items():
                fig.add_hline(y=val, line_color=colors[label], annotation_text=f"{label} : {val:.2f}$", annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
