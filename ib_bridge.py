from ib_insync import *

def executer_plan_moons(ticker_str, qty, entry_px, stop_px, tp_px):
    ib = IB()
    try:
        # Connexion au compte de simulation
        ib.connect('127.0.0.1', 7497, clientId=10)
        
        # Définition du contrat
        contract = Stock(ticker_str, 'SMART', 'USD')
        ib.qualifyContracts(contract)
        
        # Création du Bracket Order (L'ordre parent + les deux protections)
        # On utilise des ordres "LMT" (Limit) pour respecter tes calculs C2/TP
        parent = LimitOrder('BUY', qty, entry_px)
        parent.transmit = False
        
        stop_loss = StopOrder('SELL', qty, stop_px)
        stop_loss.parentId = parent.orderId
        stop_loss.transmit = False
        
        take_profit = LimitOrder('SELL', qty, tp_px)
        take_profit.parentId = parent.orderId
        take_profit.transmit = True # Transmet tout le groupe d'un coup
        
        # Envoi à TWS
        bracket = [parent, stop_loss, take_profit]
        for o in bracket:
            ib.placeOrder(contract, o)
            
        print(f"✅ Ordres envoyés pour {ticker_str} à {entry_px}$")
        ib.disconnect()
        return True
    except Exception as e:
        print(f"❌ Erreur Bridge : {e}")
        return False
