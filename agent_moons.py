import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Expert Fibo-Style", layout="wide")
st.title("🏦 Terminal Expert : Visualisation TradingView")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="AAPL").upper()
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

            # --- CALCULS FIBONACCI ---
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            
            # Définition des niveaux comme sur ta capture
            levels = {
                "0 (Top)": swing_high,
                "0.236": swing_high - (0.236 * diff),
                "0.382": swing_high - (0.382 * diff),
                "0.5": swing_high - (0.5 * diff),
                "0.618": swing_high - (0.618 * diff),
                "0.786": swing_high - (0.786 * diff),
                "1 (Bottom)": swing_low,
                "1.618 (Extension)": swing_high + (0.618 * diff)
            }
            
            px_actuel = df_m['Close'].iloc[-1]

            # --- HEADER ---
            st.metric(f"💰 Valeur actuelle : {ticker}", f"{px_actuel:.2f} $")

            # --- GRAPHIQUE ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            
            # Candlestick
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone de Soldes Pastel (Déplacée à gauche)
            fig.add_hrect(
                y0=levels["0.618"], y1=levels["0.5"], 
                fillcolor="rgba(255, 215, 0, 0.15)", line_width=0, 
                annotation_text="ZONE DE SOLDES", annotation_position="top left",
                row=1, col=1
            )
            
            # --- AJOUT DES LIGNES STYLE TRADINGVIEW ---
            colors = {
                "0 (Top)": "gray", "0.236": "red", "0.382": "orange", 
                "0.5": "green", "0.618": "teal", "0.786": "blue", 
                "1 (Bottom)": "black", "1.618 (Extension)": "cyan"
            }

            for label, val in levels.items():
                fig.add_hline(
                    y=val, 
                    line_color=colors.get(label, "white"), 
                    line_width=1,
                    annotation_text=f"{label} ({val:.2f}$)", 
                    annotation_position="bottom right",
                    row=1, col=1
                )

            # Volume
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            v_colors = ['#26a69a' if v > vol_moyen else '#ef5350' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], name='Volume', marker_color=v_colors, opacity=0.8), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # --- RÉSUMÉ DES NIVEAUX ---
            st.write("### 📝 Récapitulatif des Prix")
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**Entrée 0.5 :** {levels['0.5']:.2f}$")
            c2.write(f"**Plancher 0.618 :** {levels['0.618']:.2f}$")
            c3.write(f"**Objectif 1.618 :** {levels['1.618 (Extension)']:.2f}$")
            c4.write(f"**Stop 0.786 :** {levels['0.786']:.2f}$")
                
    except Exception as e:
        st.error(f"Erreur : {e}")            diff = swing_high - swing_low
            
            p_entree_suggere = swing_high - (0.5 * diff)   # Niveau 0.5
            p_chute_max = swing_high - (0.618 * diff)       # Niveau 0.618 (Plancher)
            p_invalidation = swing_high - (0.786 * diff)    # Niveau 0.786
            p_objectif_max = swing_high + (0.618 * diff)    # Extension 1.618
            
            px_actuel = df_m['Close'].iloc[-1]

            # --- ANALYSE DU VOLUME ---
            vol_actuel = df_m['Volume'].iloc[-1]
            vol_moyen = df_m['Volume'].rolling(20).mean().iloc[-1]
            ratio_vol = vol_actuel / vol_moyen

            # --- SÉMANTIQUE DE TENDANCE ---
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            titre_tendance = "Anticipation de hausse" if px_actuel > (h26 + l26).iloc[-1]/2 else "Anticipation de croissance"

            # --- AFFICHAGE PRIX EN TEMPS RÉEL ---
            st.metric(f"💰 Valeur actuelle de {ticker}", f"{px_actuel:.2f} $")

            # --- ALERTE VOLUME ---
            if ratio_vol >= 1.5:
                st.success(f"💎 **VOLUME EXPLOSIF ({ratio_vol:.1f}x)** : Forte conviction des acheteurs. Signal très robuste.")
            elif ratio_vol >= 1.0:
                st.info(f"✅ **VOLUME CONFIRMÉ ({ratio_vol:.1f}x)** : Activité saine, le mouvement est soutenu.")
            else:
                st.warning(f"⚠️ **VOLUME FAIBLE ({ratio_vol:.1f}x)** : Attention, le rebond manque de force. Risque de stagnation.")

            # --- CAS 1 : ANALYSE DU SIGNAL ---
            if btn_analyse:
                st.subheader(f"🔍 Analyse : {ticker}")
                if p_chute_max <= px_actuel <= p_entree_suggere:
                    st.success(f"🔥 {titre_tendance.upper()} VALIDÉE")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("PRIX D'ENTRÉE (0.5)", f"{p_entree_suggere:.2f} $")
                    c2.metric("PRIX PLANCHER (0.618)", f"{p_chute_max:.2f} $")
                    c3.metric("PRIX OBJECTIF (1.618)", f"{p_objectif_max:.2f} $")
                else:
                    st.warning(f"Le prix actuel ({px_actuel:.2f} $) est hors de la zone idéale de {p_chute_max:.2f}$ - {p_entree_suggere:.2f}$.")

            # --- CAS 2 : ANTICIPATION DES SOLDES ---
            if btn_anticipe:
                st.subheader(f"📉 {titre_tendance} : {ticker}")
                st.info(f"L'agent anticipe les niveaux de prix suivants pour profiter des soldes :")
                c1, c2, c3 = st.columns(3)
                c1.metric("DÉBUT DES SOLDES (0.5)", f"{p_entree_suggere:.2f} $")
                c2.metric("CHUTE MAX PRÉVUE (0.618)", f"{p_chute_max:.2f} $", delta="Plancher", delta_color="inverse")
                c3.metric("GAIN MAX VISÉ", f"{p_objectif_max:.2f} $")
                st.write(f"⚠️ *Note : Si le prix chute sous le plancher de **{p_chute_max:.2f} $**, la structure haussière est cassée.*")

            # --- GRAPHIQUE AVEC ZONE PASTEL ---
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            
            # Candlestick
            fig.add_trace(go.Candlestick(x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'], name='Prix'), row=1, col=1)
            
            # Zone de soldes Pastel
            fig.add_hrect(y0=p_chute_max, y1=p_entree_suggere, fillcolor="rgba(255, 215, 0, 0.2)", line_width=0, annotation_text="ZONE DE SOLDES (Pastel)", row=1, col=1)
            
            # Lignes de niveaux en prix réels
            fig.add_hline(y=p_entree_suggere, line_color="green", annotation_text=f"Entrée: {p_entree_suggere:.2f}$", row=1, col=1)
            fig.add_hline(y=p_chute_max, line_color="red", line_dash="dash", annotation_text=f"Plancher: {p_chute_max:.2f}$", row=1, col=1)
            fig.add_hline(y=p_objectif_max, line_color="cyan", annotation_text=f"Objectif: {p_objectif_max:.2f}$", row=1, col=1)

            # Volume coloré
            v_colors = ['green' if v > vol_moyen else 'red' for v in df_m['Volume']]
            fig.add_trace(go.Bar(x=df_m.index, y=df_m['Volume'], name='Volume', marker_color=v_colors, opacity=0.5), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur technique : {e}")
