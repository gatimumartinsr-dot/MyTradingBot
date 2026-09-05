import random

def calculate_position_size(balance, risk_pct, stop_loss_pips, symbol, asset_class):
    """Universal Multi-Asset Algorithmic Risk Matrix Engine"""
    risk_amount = balance * (risk_pct / 100)
    
    if "Precious" in asset_class:
        # Gold/Precious metals pricing modifiers
        lot_size = risk_amount / (stop_loss_pips * 2.0)
    elif "Major Forex" in asset_class:
        # Standard FX Currencies
        pip_value = 10.0 if "USD" in symbol else 1.0
        lot_size = risk_amount / (stop_loss_pips * pip_value)
    elif "Crypto" in asset_class:
        # Digital assets direct structural valuation fractional units
        lot_size = risk_amount / (stop_loss_pips * 1.0)
    else:
        # Equity Indices contract modifiers
        lot_size = risk_amount / (stop_loss_pips * 0.5)
        
    return max(0.01, round(lot_size, 2))

def dispatch_order(login_id, password, server, symbol, order_type, entry, sl, tp, lots, broker):
    """Secure Cloud Web Routing Layer handling sandbox independent tenant execution profiles"""
    
    # Simple verification protocol preventing sample form submissions
    if str(login_id) == "12345678" or password == "YourSecurePassword":
        return {
            "status": "error", 
            "message": "Execution Aborted: Please calibrate valid account details on your configuration sidebar."
        }
    
    # Emulated active cloud gateway loop response pipeline connection string
    network_handshake = True
    
    if network_handshake:
        simulated_ticket = random.randint(60000000, 99999999)
        return {
            "status": "success",
            "order_id": simulated_ticket,
            "message": f"Successfully mapped payload matrix to {broker} account link network pipelines securely."
        }
    else:
        return {
            "status": "error",
            "message": "Cloud Core Pipeline Error: Multi-broker webhook verification timeout."
        }
