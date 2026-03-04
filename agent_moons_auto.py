cat <<EOF > agent_moons_auto.py
from ib_insync import *
import yfinance as yf
import pandas as pd

def analyze_and_trade(symbol, qty):
    print(f"🔍 Analyse de {symbol} en cours...")
    df = yf.download(symbol, period="100d", interval="1d", progress=False)
    
    # 1. Intelligence Ichimoku
    high_9 = df['High'].rolling(window=9).max()
    low_9 = df['Low'].rolling(window=9).min()
    df['tenkan_sen'] = (high_9 + low_9) / 2
    
    high_26 = df['High'].rolling(window=26).max()
    low_26 = df['Low'].rolling(window=26).min()
    df['kijun_sen'] = (high_26 + low_26) / 2

    last_price = df['Close'].iloc[-1]
    is_bullish = last_price > df['tenkan_sen'].iloc[-1] > df['kijun_sen'].iloc[-1]

    if not is_bullish:
        print(f"❌ {symbol} : Conditions Ichimoku non remplies (Tendance neutre ou baissière).")
        return

    # 2. Intelligence Fibonacci
    high_fib = df['High'].max()
    low_fib = df['Low'].min()
    diff = high_fib - low_fib
    c2 = low_fib + (0.618 * diff)
    tp2 = low_fib + (1.618 * diff)
    stop = low_fib - (0.05 * diff)

    print(f"✅ {symbol} est Haussier ! Préparation de l'ordre...")
    
    # 3. Exécution TWS
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7497, clientId=10)
        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)
        
        bracket = ib.bracketOrder('BUY', qty, round(c2, 2), round(tp2, 2), round(stop, 2))
        for o in bracket:
            ib.placeOrder(contract, o)
            
        print(f"🚀 ORDRE AUTOMATIQUE ENVOYÉ pour {symbol} : Entrée à {c2:.2f}")
        ib.disconnect()
    except Exception as e:
        print(f"❌ Erreur connexion TWS : {e}")

if __name__ == "__main__":
    actions = ['MSI', 'NVDA', 'META', 'AAPL']
    for a in actions:
        analyze_and_trade(a, 10)
EOF
