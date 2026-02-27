import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Terminal Soldes Fibonacci", layout="wide")
st.title("🏦 Terminal Expert : Anticipation des Soldes (Golden Pocket)")

with st.sidebar:
    st.header("⚙️ Configuration")
    ticker = st.text_input("🔍 Symbole", value="TSLA").upper()
    capital = st.number_input("💰 Capital ($)", value=10000)
    risk_pc = st.slider("⚠️ Risque (%)", 0.5, 5.0, 1.0) / 100

if st.button("Anticiper les Soldes"):
    try:
        df = yf.download(ticker, period="60d", interval="1d", auto_adjust=True, progress=False)
        df_m = yf.download(ticker, period="15d", interval="15m", auto_adjust=True, progress=False)
        
        if df.empty or df_m.empty:
            st.error("❌ Données introuvables.")
        else:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if isinstance(df_m.columns, pd.MultiIndex): df_m.columns = df_m.columns.get_level_values(0)

            # --- CALCULS ICHIMOKU (Pour le Stop) ---
            h26, l26 = df_m['High'].rolling(26).max(), df_m['Low'].rolling(26).min()
            kijun = (h26 + l26) / 2
            h9, l9 = df_m['High'].rolling(9).max(), df_m['Low'].rolling(9).min()
            tenkan = (h9 + l9) / 2
            
            # --- CALCULS FIBONACCI (Les Soldes) ---
            swing_high = df['High'].tail(30).max()
            swing_low = df['Low'].tail(30).min()
            diff = swing_high - swing_low
            
            prix_solde_618 = swing_high - (0.618 * diff)
            prix_solde_05 = swing_high - (0.5 * diff)
            
            px_actuel = df_m['Close'].iloc[-1]
            
            # --- LOGIQUE D'ANTICIPATION ---
            st.subheader(f"📊 Analyse des soldes pour {ticker}")
            
            # Si on est au-dessus des soldes, on anticipe
            if px_actuel > prix_solde_05:
                st.info(f"🚀 L'action est actuellement en haut. L'agent anticipe une zone de 'soldes' entre **{prix_solde_618:.2f} $** et **{prix_solde_05:.2f} $**.")
                
                # Calcul basé sur l'entrée idéale à 0.618
                entree_anticipee = prix_solde_618
                stop_theorique = kijun.iloc[-1]
                
                # Sécurité : si la Kijun est déjà plus haute que les soldes, on utilise le niveau 0.786 ou le nuage
                if stop_theorique >= entree_anticipee:
                    stop_theorique = swing_high - (0.786 * diff)

                qte_anticipee = int((capital * risk_pc) / abs(entree_anticipee - stop_theorique))
                
                c1, c2, c3 = st.columns(3)
                c1.metric("PRIX D'ENTRÉE ANTICIPÉ", f"{entree_anticipee:.2f} $", "Cible 0.618")
                c2.metric("STOP PRÉVU", f"{stop_theorique:.2f} $")
                c3.metric("QUANTITÉ À PRÉPARER", f"{qte_anticipee}")
                
                st.write(f"💡 *Conseil : Vous pouvez placer un ordre 'Limit' à {entree_anticipee:.2f} $ pour ne pas manquer le rebond.*")
            
            elif px_actuel < prix_solde_618:
                st.error(f"⚠️ Soldes terminées : Le prix ({px_actuel:.2f} $) a chuté sous les 0.618. La structure est compromise.")
            else:
                st.success(f"✅ ON Y EST ! Le prix est dans la Golden Pocket ({px_actuel:.2f} $).")

            # --- GRAPHIQUE DES SOLDES ---
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Prix'))
            
            # Zone des soldes
            fig.add_hrect(y0=prix_solde_618, y1=prix_solde_05, fillcolor="gold", opacity=0.2, annotation_text="ZONE DE SOLDES (0.5 - 0.618)")
            
            # Flèche d'anticipation
            fig.add_annotation(x=df.index[-1], y=prix_solde_618, text="ENTRÉE ICI", showarrow=True, arrowhead=1, bgcolor="green")

            fig.update_layout(template="plotly_dark", height=500, title=f"Anticipation Fibonacci : {ticker}")
            st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur : {e}")
