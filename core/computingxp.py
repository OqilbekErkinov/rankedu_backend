def compute_xp(category, title):
    title = (title or "").upper()

    if category == "international_cert":
        if "C2" in title: return 3000
        if "C1" in title: return 2500
        if "B2" in title: return 2000
        if "B1" in title: return 1500
        if "A2" in title: return 1000
        if "A1" in title: return 500

    if category == "national_cert":
        if "A+" in title: return 2000
        if "A" in title: return 1700
        if "B+" in title: return 1400
        if "B" in title: return 1100
        if "C+" in title: return 800
        if "C" in title: return 500

    if category == "intl_article":
        return 500

    if category == "rep_article":
        return 180

    if category == "activity":
        if "winner1" in title: return 1000
        if "winner2" in title: return 700
        if "winner3" in title: return 400
        return 100

    return 0