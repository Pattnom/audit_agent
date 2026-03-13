def calculate_refund(profile: str, data: dict, eligibility: dict) -> dict:
    """
    Compute refund amount for electricity and/or gas.
    Returns dict with totals and breakdown.
    """
    refund = {}
    total = 0.0

    # Electricity
    if eligibility.get("electricity", {}).get("eligible"):
        consumption = data.get("electricity_consumption_mwh", 0)
        # 2024-2025: normal 22.5, reduced 0.5
        if profile == "agriculture":
            # Agricultural rate: 1.0 or 0.5 if electro-intensive (but we ignore for simplicity)
            reduced_rate = 1.0
        else:
            reduced_rate = 0.5
        gain_per_mwh = 22.5 - reduced_rate
        electricity_refund = consumption * gain_per_mwh
        refund["electricity"] = electricity_refund
        total += electricity_refund

    # Gas
    if eligibility.get("gas", {}).get("eligible"):
        consumption = data.get("gas_consumption_mwh", 0)
        # Need normal rate; could be extracted from invoices or use default.
        # For simplicity, we assume normal rate is 16.37 €/MWh (2024).
        normal_rate = 16.37  # approximate; ideally from data
        gas_refund = consumption * normal_rate
        refund["gas"] = gas_refund
        total += gas_refund

    refund["total"] = total
    return refund