import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Intelligence", layout="wide")
st.title("🏦 Terminal Expert : Analyse de Confluence & Décision")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    lookback = st.slider("Fenêtre du Swing (jours)", 7, 60, 30)

col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser le Signal Actuel")
btn_anticipe = col_btn2.button("📉 Anticiper : Acheter ou Vendre")

if btn_analyse or btn_anticipe:
    try:
        # Données
        df = yf.download(ticker, period=f"{lookback+20}d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="10d", interval="15m", auto_adjust=True, progress=False)
        
        if not df.empty and not df_m.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ANALYTIQUES ---
            px_actuel = df_m['Close'].iloc[-1]
            swing_high, swing_low = df['High'].tail(lookback).max(), df['Low'].tail(lookback).min()
            diff = swing_high - swing_low
            
            fibo = {
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "1.618": swing_high + (0.618 * diff)
            }

            # Tendance (MA20) & Momentum (RSI simplifié)
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            perte = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / perte
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            vol_confirm = df_m['Volume'].iloc[-1] > vol_moyen * 1.3

            # --- 1. AFFICHAGE PRIX LIVE ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center; color: #1E90FF;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            
            # État du Marché
            tend_label = "HAUSSIER 🟢" if px_actuel > ma20 else "BAISSIER 🔴"
            rsi_label = "SURACHAT ⚠️" if rsi > 70 else "SURVENTE 📉" if rsi < 30 else "NEUTRE ⚖️"
            st.markdown(f"<h3 style='text-align: center;'>Tendance : {tend_label} | Momentum : {rsi_label} (RSI: {rsi:.0f})</h3>", unsafe_allow_html=True)
            st.divider()

            # --- 2. LE VERDICT DE L'AGENT ---
            st.subheader("🤖 Verdict de l'Agent")
            
            # Logique de décision
            is_in_fibo = fibo["0.786"] <= px_actuel <= fibo["0.5"]
            is_overextended = px_actuel >= fibo["1.618"] * 0.97
            
            if is_in_fibo:
                if px_actuel > ma20 and vol_confirm:
                    st.success("🔥 SIGNAL D'ACHAT FORT : Confluence Fibo + Tendance + Volume.")
                elif rsi < 30:
                    st.success("🛒 ACHAT OPPORTUNISTE : Zone de soldes + Survente extrême.")
                else:
                    st.info("🟡 ATTENTE : Zone de soldes atteinte, mais manque de volume ou tendance adverse.")
            elif is_overextended:
                st.error("🚨 SIGNAL DE VENTE : Objectif maximum atteint. Risque de retournement élevé.")
            else:
                st.write("🔭 OBSERVATION : Aucun signal majeur. Le prix cherche sa direction.")

            # --- 3. RÉCAPITULATIF FINANCIER ---
            dist_stop = abs(px_actuel - fibo["0.786"])
            qte = int((capital * risk_pc) / dist_stop) if dist_stop > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Risque (10%)", f"-{(qte * dist_stop):.2f} $")
            c2.metric("Quantité", f"{qte} titres")
            c3.metric("Objectif Max", f"{fibo['1.618']:.2f} $")

            # --- 4. GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zones
            fig.add_hrect(y0=fibo["0.786"], y1=fibo["0.5"], fillcolor="rgba(0, 255, 0, 0.1)", line_width=0, annotation_text="SOLDES", annotation_position="top left", row=1, col=1)
            fig.add_hrect(y0=fibo["1.618"]*0.98, y1=fibo["1.618"]*1.02, fillcolor="rgba(255, 0, 0, 0.1)", line_width=0, annotation_text="VENTE MAX", annotation_position="top left", row=1, col=1)
            
            for k, v in fibo.items():
                fig.add_hline(y=v, line_color="rgba(255, 255, 255, 0.2)", annotation_text=f"{k} ({v:.2f}$)", annotation_position="bottom right", row=1, col=1)

            # Volume
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], marker_color=v_colors, name='Volume'), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
