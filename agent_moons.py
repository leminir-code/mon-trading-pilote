import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Terminal Moons Validation Expert", layout="wide")
st.title("🏦 Terminal Expert : Validation Manuelle des Swings")

with st.sidebar:
    st.header("⚙️ Paramètres")
    ticker = st.text_input("🔍 Symbole", value="MSI").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque par trade (%)", 0.5, 15.0, 10.0) / 100
    
    st.divider()
    mode = st.radio("Direction du Trade", ["ACHAT (Long)", "VENTE (Short)"])
    lookback = st.slider("Fenêtre de recherche (jours)", 15, 120, 60)
    
    st.divider()
    st.header("🧪 Test Historique")
    # L'utilisateur entre la date manuellement ici après avoir consulté le tableau
    test_date_input = st.date_input("Date d'entrée à tester", value=datetime.now().date() - timedelta(days=7))

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
    
    conds = [px > max(sa.iloc[-1], sb.iloc[-1]) if mode_trade == "ACHAT (Long)" else px < min(sa.iloc[-1], sb.iloc[-1]),
             sa.iloc[-1] > sb.iloc[-1] if mode_trade == "ACHAT (Long)" else sa.iloc[-1] < sb.iloc[-1],
             tenkan.iloc[-1] > kijun.iloc[-1] if mode_trade == "ACHAT (Long)" else tenkan.iloc[-1] < kijun.iloc[-1],
             chikou_lib]
    return sum(conds), tenkan, kijun, sa, sb

def find_top_swings(data, mode_trade, n=2):
    col = 'High' if mode_trade == "ACHAT (Long)" else 'Low'
    swings = []
    df_temp = data.copy()
    for _ in range(n):
        idx = df_temp[col].idxmax() if mode_trade == "ACHAT (Long)" else df_temp[col].idxmin()
        swings.append({'Date': idx.strftime('%Y-%m-%d'), 'Prix': round(df_temp.loc[idx, col], 2)})
        df_temp = df_temp.drop(index=idx)
    return pd.DataFrame(swings)

# --- BOUTONS ---
col_btn1, col_btn2 = st.columns(2)
btn_analyse = col_btn1.button("🚀 Analyser & Identifier Swings")
btn_test = col_btn2.button("🧪 Lancer l'Essai sur Date Saisie")

if btn_analyse or btn_test:
    try:
        df_d = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        df_15 = yf.download(ticker, period="60d", interval="15m", auto_adjust=True, progress=False)
        
        if not df_d.empty and not df_15.empty:
            if isinstance(df_d.columns, pd.MultiIndex): df_d.columns = df_d.columns.get_level_values(0)
            if isinstance(df_15.columns, pd.MultiIndex): df_15.columns = df_15.columns.get_level_values(0)

            px_actuel = df_15['Close'].iloc[-1]
            
            # --- 1. IDENTIFICATION DES SWINGS (POUR L'UTILISATEUR) ---
            swings_df = find_top_swings(df_d.tail(lookback), mode)
            
            st.divider()
            st.subheader("🔍 Swings Majeurs Détectés (Choisissez une date pour le test)")
            st.table(swings_df)
            
            # --- 2. CALCUL DES NIVEAUX (BASÉS SUR LE SWING LE PLUS RÉCENT) ---
            last_swing_val = swings_df.iloc[0]['Prix']
            base_ref = df_d.tail(lookback)['Low'].min() if mode == "ACHAT (Long)" else df_d.tail(lookback)['High'].max()
            diff = abs(last_swing_val - base_ref)
            
            f_levels = {
                "0.5": last_swing_val - (0.5 * diff) if mode == "ACHAT (Long)" else last_swing_val + (0.5 * diff),
                "0.618": last_swing_val - (0.618 * diff) if mode == "ACHAT (Long)" else last_swing_val + (0.618 * diff),
                "0.786": last_swing_val - (0.786 * diff) if mode == "ACHAT (Long)" else last_swing_val + (0.786 * diff),
                "1.618": last_swing_val + (0.618 * diff) if mode == "ACHAT (Long)" else last_swing_val - (0.618 * diff)
            }

            # --- 3. MODULE DE TEST (SI BOUTON TEST) ---
            if btn_test:
                st.subheader(f"📊 Résultat du test depuis le {test_date_input}")
                sim_ts = pd.Timestamp(test_date_input).tz_localize(df_15.index.tz)
                hist_test = df_15[df_15.index >= sim_ts]
                
                trigger = hist_test[hist_test['Low'] <= f_levels["0.618"]] if mode == "ACHAT (Long)" else hist_test[hist_test['High'] >= f_levels["0.618"]]
                
                if not trigger.empty:
                    px_e = f_levels["0.618"]
                    qty = int((capital * risk_pc) / abs(px_e - f_levels["0.786"]))
                    post = hist_test[hist_test.index >= trigger.index[0]]
                    hit_t = post[post['High'] >= f_levels["1.618"]] if mode == "ACHAT (Long)" else post[post['Low'] <= f_levels["1.618"]]
                    hit_s = post[post['Low'] <= f_levels["0.786"]] if mode == "ACHAT (Long)" else post[post['High'] >= f_levels["0.786"]]
                    
                    st.info(f"📍 Entrée à {px_e:.2f}$ | Quantité: {qty} titres")
                    if not hit_t.empty and (hit_s.empty or hit_t.index[0] < hit_s.index[0]):
                        st.success(f"🎯 RÉUSSITE : Gain de **+{(abs(f_levels['1.618'] - px_e)*qty):,.2f} $**")
                    elif not hit_s.empty:
                        st.error(f"🛑 STOP LOSS : Perte de **-{(abs(px_e - f_levels['0.786'])*qty):,.2f} $**")
                else:
                    st.info("Le prix n'a pas atteint le niveau d'entrée (0.618) après cette date.")

            # --- 4. GRAPHIQUE ---
            df_plot = df_15.tail(600)
            fig = make_subplots(rows=1, cols=1)
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Prix'))
            
            # Retracements : Zone Gauche / Prix Droite
            fig.add_hrect(y0=f_levels["0.786"], y1=f_levels["0.618"], fillcolor="rgba(0, 255, 0, 0.1)", line_width=0, annotation_text="ZONE ACTION", annotation_position="top left")
            for lbl, val in f_levels.items():
                fig.add_hline(y=val, line_dash="dot", line_color="rgba(255,255,255,0.4)", annotation_text=f"{lbl}: {val:.2f}$", annotation_position="bottom right")

            fig.update_layout(template="plotly_dark", height=750, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
