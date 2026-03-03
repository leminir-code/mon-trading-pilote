from ib_insync import *

# 1. Création de l'objet de connexion
ib = IB()

try:
    # 2. Tentative de connexion sur le port de simulation (7497)
    ib.connect('127.0.0.1', 7497, clientId=1)
    print("✅ SUCCÈS : Ton robot est maintenant lié à ton compte de simulation !")

    # 3. Demander le prix de NVIDIA (NVDA) pour tester tes flux payants
    contract = Stock('NVDA', 'SMART', 'USD')
    ib.qualifyContracts(contract)
    
    ticker = ib.reqMktData(contract)
    ib.sleep(2) # On attend 2 secondes pour recevoir la donnée
    
    print(f"📈 Prix de NVDA en direct (Simulé) : {ticker.last} $")

    # 4. Déconnexion propre
    ib.disconnect()

except Exception as e:
    print(f"❌ ERREUR : {e}")
    print("Vérifie que TWS est bien ouvert avec le bandeau ROUGE.")
