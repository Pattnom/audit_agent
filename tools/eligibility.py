def check_electricity_eligibility(data: dict) -> dict:
    """Return dict with 'eligible' bool, 'reason' if not, and computed ratio."""
    cost = data.get("electricity_cost_euro")
    va = data.get("value_added_euro")
    if not cost or not va or va == 0:
        return {"eligible": False, "reason": "Missing cost or value added", "ratio": None}
    ratio = (cost / va) * 100
    eligible = ratio >= 0.5
    reason = None if eligible else f"Electro-intensity ratio {ratio:.2f}% < 0.5%"

    # Also need production share >= 50%
    prod_share = data.get("production_share_percent")
    if prod_share is None:
        # If missing, we might assume 100% or ask? We'll treat as missing.
        return {"eligible": False, "reason": "Missing production share", "ratio": ratio}
    if prod_share < 50:
        return {"eligible": False, "reason": f"Production share {prod_share}% < 50%", "ratio": ratio}

    return {"eligible": eligible, "reason": reason, "ratio": ratio}

def check_gas_eligibility(data: dict) -> dict:
    """Check gas usage eligibility based on process description."""
    process = data.get("process_description", "").lower()
    # Keywords from L312-37
    keywords = [
        "réduction chimique", "électrolyse", "procédés métallurgiques",
        "fusion", "forgeage", "traitements thermiques",
        "fabrication de produits minéraux non métalliques",
        "verre", "céramique", "ciment", "serre", "cogénération"
    ]
    eligible = any(kw in process for kw in keywords)
    reason = None if eligible else "Process description does not mention an eligible usage"
    return {"eligible": eligible, "reason": reason}