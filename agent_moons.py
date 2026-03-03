import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Pro : Intelligence Flux", layout="wide")
st.title("🏦 Terminal Expert : Gestion Multi-Cibles & Sécurité")

# --- AJOUT DE LA DOCUMENTATION (SANS CHANGER LE PROGRAMME) ---
with st.expander("📖 DOCUMENTATION & ALGORITHME DE L'AGENT"):
    st.markdown("""
    ### 1. Logique de l'Algorithme
    * **Acquisition** : Flux hybride Daily (1 an) / 15min (60j).
    * **Pivot Dynamique (T1)** : Identification du sommet/creux majeur selon l'ATR et le lookback.
    * **Confluence Ichimoku** : Score sur 4 définissant l'état (Haussier/Baissier).
    * **Projection Fibonacci** : Calcul de C2 (0.618), Soldes (0.786) et Stop (0.95).
    * **Sécurité Kumo** : Plafonnement de C3 (Sortie) à la lisière du nuage en contre-tendance.
    * **Gestion du Risque** : Calcul de quantité basé sur le capital (10k$) et le risque choisi.

    ### 2. Nomenclature des Affichages
    * **C1** : T1 Valeur Pivot (Date & Prix).
    * **C2** : Prix d'entrée (Zone d'exécution).
    * **C3** : Prix de vente final (TP2).
    * **C4** : Filtre Dynamique (Écart ATR en jours).
    * **TP1 / TP2 / TP3** : Sorties échelonnées (50% / 30% / 20%).
    * **Labels** : Affichage impératif à gauche du graphique.
    """)

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="META").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    
    st.divider()
    risk_pc = st.slider("Risque par trade (%)", 0.5, 15.0, 5.0) / 100
    lookback_max = st.slider("Fenêtre Max du Swing (jours)", 15, 120, 90)

# --- FONCTIONS TECHNIQUES ---
def get_ichimoku_score(data, mode_trade):
    if len(data) < 52: return 0, None, None, None, None
    px = data['Close'].iloc[-1]
    h9, l9 = data['High'].rolling(9).max(), data['Low'].rolling(9).min()
    tenkan = (h9 + l9) / 2
    h26, l26 = data['High'].rolling(26).max(), data['Low'].rolling(26).min()
    kijun = (h26 + l26) / 2
    sa = ((tenkan + kijun) / 2).shift(26)
    sb = ((data['High'].rolling(52).max() + data['Low'].rolling(52).min()) / 2).shift(26)
    chikou_lib = px > data['Close'].shift(26).iloc[-1] if mode_trade == "ACHAT (Long)" else px < data['Close'].shift(26).iloc[-1]
    
    if mode_trade == "ACHAT (Long)":
        conds = [px > max(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] > sb.iloc[-1], tenkan.iloc[-1] > kijun.iloc[-1], chikou_lib]
    else:
        conds = [px < min(sa.iloc[-1], sb.iloc[-1]), sa.iloc[-1] < sb.iloc[-1], tenkan.iloc[-1] < kijun.iloc[-1], chikou_lib]
    return sum(conds), sa, sb

def calculate_atr(data, period=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    return np.max(ranges, axis=1).rolling(period).mean()

def find_dynamic_swings(data, mode_trade, atr_val):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    price_avg = data['Close'].mean()
    dynamic_dist = max(3, int((atr_val / price_avg) * 500)) 
    swings = []
    df_temp = data.copy().sort_values(by=col, ascending=(mode_trade == "VENTE (Short)"))
    for idx, row in df_temp.iterrows():
        if all(abs((idx - pd.to_datetime(s['Date'])).days) >= dynamic_dist for s in swings):
            swings.append({'Date': idx.strftime('%Y-%m-%d'), 'Prix': round(row[col], 2)})
        if len(swings) >= 2: break
    return pd.DataFrame(swings), dynamic_dist

# --- BOUTONS D'ACTION ---
col_btn1, col_btn2, col_btn3 = st.columns(3)
btn_analyse = col_btn1.button("🚀 Analyser la Confluence")
btn_anticipe = col_btn2.button("📈 Anticiper : Plan de Trade")
btn_save = col_btn3.button("💾 Sauvegarder le Plan")

if btn_analyse or btn_anticipe or btn_save:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]
            atr_d = calculate_atr(df_d).iloc[-1]
            df_recent = df_d.tail(lookback_max)
            swings_df, dist_calculee = find_dynamic_swings(df_recent, mode, atr_d)
            
            t1_pivot = swings_df.iloc[0]['Prix'] 
            base_ref = df_recent['Low'].min() if mode == "ACHAT (Long)" else df_recent['High'].max()
            diff = abs(t1_pivot - base_ref)
            
            # --- CALCULS ---
            f_entree = t1_pivot - (0.618 * diff) if mode == "ACHAT (Long)" else t1_pivot + (0.618 * diff)
            f_soldes = t1_pivot - (0.786 * diff) if mode == "ACHAT (Long)" else t1_pivot + (0.786 * diff)
            f_stop = t1_pivot - (0.95 * diff) if mode == "ACHAT (Long)" else t1_pivot + (0.95 * diff)
            
            score_trend, sa_d, sb_d = get_ichimoku_score(df_d, mode)
            trend_label = "HAUSSIER 📈" if score_trend >= 3 else "BAISSIER 📉" if score_trend <= 1 else "NEUTRE ⚖️"
            trend_color = "#00FF00" if trend_label == "HAUSSIER 📈" else "#FF0000" if trend_label == "BAISSIER 📉" else "#FFA500"

            kumo_limit = min(sa_d.iloc[-1], sb_d.iloc[-1]) if mode == "ACHAT (Long)" else max(sa_d.iloc[-1], sb_d.iloc[-1])
            is_contre_tendance = (mode == "ACHAT (Long)" and trend_label == "BAISSIER 📉") or (mode == "VENTE (Short)" and trend_label == "HAUSSIER 📈")
            
            tp2_final = kumo_limit if is_contre_tendance else (t1_pivot + (0.618 * diff) if mode == "ACHAT (Long)" else t1_pivot - (0.618 * diff))
            tp1_secure = (f_entree + tp2_final) / 2
            tp3_grand_profit = t1_pivot + (1.618 * diff) if mode == "ACHAT (Long)" else t1_pivot - (1.618 * diff)

            # --- AFFICHAGE MÉTRIQUES ---
            st.divider()
            st.markdown(f"<h1 style='text-align: center;'>{ticker} : {px_actuel:.2f} $</h1>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: center; color: {trend_color};'>Marché {trend_label}</h3>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("C1 (T1 Valeur Pivot)", swings_df.iloc[0]['Date'], f"{t1_pivot:.2f} $")
            c2.metric("C2 (Prix d'entrée)", f"{f_entree:.2f} $")
            c3.metric("C3 (Prix de vente TP2)", f"{tp2_final:.2f} $")
            c4.metric("C4 (Filtre Dynamique)", f"{dist_calculee} jrs")
            st.divider()

            if btn_analyse:
                st.subheader("🚀 Diagnostic de Confluence & Historique")
                st.write("**Dates de swing identifiées :**")
                st.table(swings_df)
                if score_trend < 2: st.error(f"❌ TRADE NON RECOMMANDÉ : Score {score_trend}/4")
                else: st.success(f"✅ Score Ichimoku {score_trend}/4")

            elif btn_anticipe:
                st.subheader(f"📋 Ticket d'Ordre Courtage (Investissement : {capital} $)")
                qty = int((capital * risk_pc) / abs(f_entree - f_stop)) if abs(f_entree - f_stop) > 0 else 0
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.info(f"**ACCUMULATION / SOLDES**\n- **Entrée (C2) :** {f_entree:.2f} $\n- **ZONE SOLDES :** {f_soldes:.2f} $\n- **Quantité :** {qty} titres")
                with col_t2:
                    st.success(f"**SORTIES À PROFIT**\n- **TP1 (50%) :** {tp1_secure:.2f} $\n- **TP2 / C3 (30%) :** {tp2_final:.2f} $\n- **TP3 (Max 20%) :** {tp3_grand_profit:.2f} $\n- **STOP LOSS :** {f_stop:.2f} $")

            # --- GRAPHIQUE ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'), row=1, col=1)
            
            levels = {"T1 (PIVOT)": t1_pivot, "C2 (ENTRÉE)": f_entree, "SOLDES": f_soldes, "TP1": tp1_secure, "TP2": tp2_final, "TP3": tp3_grand_profit, "STOP": f_stop}
            colors = {"T1 (PIVOT)": "white", "C2 (ENTRÉE)": "cyan", "SOLDES": "yellow", "TP1": "#FFA500", "TP2": "#00FF00", "TP3": "#00FFFF", "STOP": "red"}
            for lbl, val in levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color=colors[lbl], annotation_text=f"{lbl}: {val:.2f}$", annotation_position="top left", row=1, col=1)

            _, sa_15, sb_15 = get_ichimoku_score(df_15, mode)
            fig.add_trace(go.Scatter(x=df_15.index, y=sa_15, line=dict(color='rgba(0, 255, 0, 0.1)'), name='Kumo A'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_15.index, y=sb_15, line=dict(color='rgba(255, 0, 0, 0.1)'), fill='tonexty', name='Kumo B'), row=1, col=1)
            
            v_colors = ['#26a69a' if c >= o else '#ef5350' for o, c in zip(df_plot['Open'], df_plot['Close'])]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], marker_color=v_colors), row=2, col=1)

            fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
