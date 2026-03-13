def classify_naf(naf_code: str) -> str:
    """
    Returns one of: "industrie", "agriculture", "artisan", or "ineligible"
    Based on NAF code ranges.
    """
    # Extract numeric part (first two digits)
    try:
        num_part = int(naf_code[:2])
    except:
        return "ineligible"

    # Industry: codes 05-39
    if 5 <= num_part <= 39:
        return "industrie"

    # Agriculture: divisions 01-02
    if num_part in (1, 2):
        return "agriculture"

    # Artisan transformateur: specific codes list
    artisan_codes = [
        "10.71A", "10.71B", "10.71C",  # boulangeries
        "16.23Z", "16.29Z",             # menuiserie
        "25.62A", "25.62B",             # mécanique
        # add more as needed
    ]
    if naf_code in artisan_codes:
        return "artisan"

    # Default ineligible
    return "ineligible"