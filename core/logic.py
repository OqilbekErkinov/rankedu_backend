# core/logic.py

def calculate_score(achievement):
    cat = achievement.category
    sub = achievement.sub_category or ""
    rank = achievement.rank

    # 1. Kitobxonlik (Maksimal 20 ball) [cite: 45]
    if cat == 1:
        # Sertifikat yuklangan bo'lsa maksimal ball (Nizom bo'yicha tahlil)
        return 20

    # 2. 5 muhim tashabbus (Maksimal 20 ball) [cite: 45, 47]
    if cat == 2:
        if "tashkil" in sub.lower():
            return 20
        return 10

    # 5. Ko'rik-tanlov va olimpiadalar (Maksimal 10 ball) [cite: 50]
    if cat == 5:
        if "Xalqaro" in sub:
            return 10
        if "Respublika" in sub:
            return {1: 9, 2: 8, 3: 7}.get(rank, 7)
        if "Viloyat" in sub:
            return {1: 6, 2: 5, 3: 4}.get(rank, 4)
        if "OTM" in sub:
            return {1: 3, 2: 2, 3: 1}.get(rank, 1)

    # 8. Volontyorlik (Maksimal 5 ball) [cite: 51]
    if cat == 8:
        return 5

    # 9. Madaniy tashriflar (Tizimli tahlil uchun 1 ball har biri) [cite: 54]
    if cat == 9:
        return 1

    # 10. Sport va sog'lom turmush (Maksimal 5 ball) [cite: 54]
    if cat == 10:
        if "terma jamoa" in sub.lower(): return 5
        if "seksiya" in sub.lower(): return 3
        return 1

    # 11. Boshqa ma'naviy faollik (Maksimal 5 ball) [cite: 56]
    if cat == 11:
        if "Hamkor" in sub: return 3
        if "Xiyobon" in sub or "Adiblar" in sub: return 2
        return 1

    return 0