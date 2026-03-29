import json
import requests

def get_balance(address):
    """
    Consulta balances de AVAX, USDC (Nativo) y USDC.e (Bridged).
    """
    url = "https://api.avax.network/ext/bc/C/rpc"
    
    # AVAX Balance
    payload_avax = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
    
    # USDC Contracts
    contracts = {
        "USDC_Native": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "USDC_e": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664"
    }
    
    results = {"address": address, "avax": 0, "balances": {}}
    
    try:
        r_avax = requests.post(url, json=payload_avax).json()
        results["avax"] = int(r_avax['result'], 16) / 10**18
        
        for name, contract in contracts.items():
            data = "0x70a08231" + address[2:].zfill(64)
            payload = {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": contract, "data": data}, "latest"], "id": 2}
            r = requests.post(url, json=payload).json()
            results["balances"][name] = int(r['result'], 16) / 10**6
            
        return results
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    addr = "0x185CE8a11d12FCFf4e0c50DE807aFDF60DdEEa9C"
    print(json.dumps(get_balance(addr), indent=2))
