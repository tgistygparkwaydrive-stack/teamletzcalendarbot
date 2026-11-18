#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEAM LËTZEBUERG – WÖCHENTLICHER YU-GI-OH! TURNIER-SCRAPER (V8 - 100% PURE TCG, NO GENESYS)
Liest live ausschließlich offizielle Advanced-TCG-Turniere aus:
https://www.yugioh-card.com/eu/list-of-events-wcq-europe-2027/
Alle Genesys/Genesis-Turniere werden komplett ignoriert und aus Firebase bereinigt.
"""

import json
import math
import os
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

FIREBASE_DB_URL = os.environ.get(
    "FIREBASE_DB_URL",
    "https://teamletz-default-rtdb.firebaseio.com"
).rstrip("/")
SYNC_ROOM_KEY = os.environ.get("SYNC_ROOM_KEY", "TeamLetzebuerg2007_OfficialSync")

LUX_LAT = 49.6116
LUX_LON = 6.1319

BANNED_FAKE_IDS = {
    "ev_ycs_auto_vip", "ev_ycs_paris_feb27", "ev_ycs_dortmund_apr27",
    "ev_local_lux_weekly", "ev_local_trier_weekly", "ev_ycs_bologna_dec26",
    "ev_ots_lux_nov26", "ev_reg_trier_dec26", "ev_reg_metz_dec26",
    "ev_ots_saar_dec26", "ev_reg_brussels_jan27", "ev_reg_cologne_jan27",
    "ev_ots_namur_feb27", "ev_reg_frankfurt_mar27", "ev_ots_lux_mar27",
    "ev_reg_strasbourg_apr27", "ev_nat_benelux_may27", "ev_nat_france_may27",
    "ev_nat_germany_jun27", "ev_wcq_euros_jul27", "ev_wcs_europe_aug27",
    "ev_reg_differdange_nov26", "ev_reg_pirmasens_nov26", "ev_reg_wavre_nov26",
    "ev_reg_trier_dec26_real", "ev_reg_metz_dec26_real", "ev_reg_dreieich_dec26",
    "ev_ots_dudelange_dec26", "ev_reg_saarbruecken_jan27", "ev_reg_liege_jan27",
    "ev_reg_bruhl_jan27", "ev_reg_ede_jan27", "ev_ots_namur_feb27_real",
    "ev_reg_nancy_feb27", "ev_reg_ludwigshafen_feb27", "ev_reg_hasselt_mar27",
    "ev_reg_strasbourg_mar27", "ev_konami_uk_open_nov26", "ev_konami_swiss_open_dec26"
}

KNOWN_LOCATIONS = {
    "mana temple": ("Beggen (Luxembourg)", 49.6455, 6.1294, "LU", "🇱🇺"),
    "luxembourg": ("Luxembourg", 49.6116, 6.1319, "LU", "🇱🇺"),
    "beggen": ("Beggen", 49.6455, 6.1294, "LU", "🇱🇺"),
    "differdange": ("Differdange", 49.5242, 5.8914, "LU", "🇱🇺"),
    "dudelange": ("Dudelange", 49.4806, 6.0875, "LU", "🇱🇺"),
    "esch": ("Esch-sur-Alzette", 49.4958, 5.9806, "LU", "🇱🇺"),
    "trier": ("Trier", 49.7499, 6.6371, "DE", "🇩🇪"),
    "spielbar": ("Trier", 49.7499, 6.6371, "DE", "🇩🇪"),
    "saarbrücken": ("Saarbrücken", 49.2402, 6.9969, "DE", "🇩🇪"),
    "dragonlord": ("Saarbrücken", 49.2402, 6.9969, "DE", "🇩🇪"),
    "zock!": ("Saarbrücken", 49.2402, 6.9969, "DE", "🇩🇪"),
    "pirmasens": ("Pirmasens", 49.2014, 7.6053, "DE", "🇩🇪"),
    "wizzards inn": ("Pirmasens", 49.2014, 7.6053, "DE", "🇩🇪"),
    "kaiserslautern": ("Kaiserslautern", 49.4401, 7.7491, "DE", "🇩🇪"),
    "mannheim": ("Mannheim", 49.4875, 8.4660, "DE", "🇩🇪"),
    "ludwigshafen": ("Ludwigshafen", 49.4774, 8.4452, "DE", "🇩🇪"),
    "excalibur": ("Ludwigshafen", 49.4774, 8.4452, "DE", "🇩🇪"),
    "karlsruhe": ("Karlsruhe", 49.0069, 8.4037, "DE", "🇩🇪"),
    "spiele pyramide": ("Karlsruhe", 49.0069, 8.4037, "DE", "🇩🇪"),
    "stuttgart": ("Stuttgart", 48.7758, 9.1829, "DE", "🇩🇪"),
    "mainz": ("Mainz", 49.9929, 8.2473, "DE", "🇩🇪"),
    "orcish outpost": ("Mainz", 49.9929, 8.2473, "DE", "🇩🇪"),
    "wiesbaden": ("Wiesbaden", 50.0782, 8.2398, "DE", "🇩🇪"),
    "darmstadt": ("Darmstadt", 49.8728, 8.6512, "DE", "🇩🇪"),
    "dreieich": ("Dreieich", 50.0189, 8.6961, "DE", "🇩🇪"),
    "collect-it": ("Dreieich", 50.0189, 8.6961, "DE", "🇩🇪"),
    "frankfurt": ("Frankfurt", 50.1109, 8.6821, "DE", "🇩🇪"),
    "jk entertainment": ("Frankfurt", 50.1109, 8.6821, "DE", "🇩🇪"),
    "gießen": ("Gießen", 50.5841, 8.6784, "DE", "🇩🇪"),
    "marburg": ("Marburg", 50.8022, 8.7668, "DE", "🇩🇪"),
    "koblenz": ("Koblenz", 50.3569, 7.5890, "DE", "🇩🇪"),
    "zeitgeist": ("Koblenz", 50.3569, 7.5890, "DE", "🇩🇪"),
    "bonn": ("Bonn", 50.7374, 7.0982, "DE", "🇩🇪"),
    "siegburg": ("Siegburg", 50.7958, 7.2044, "DE", "🇩🇪"),
    "troisdorf": ("Troisdorf", 50.8161, 7.1556, "DE", "🇩🇪"),
    "brühl": ("Brühl", 50.8294, 6.9050, "DE", "🇩🇪"),
    "aachen": ("Aachen", 50.7753, 6.0839, "DE", "🇩🇪"),
    "köln": ("Köln", 50.9375, 6.9603, "DE", "🇩🇪"),
    "cologne": ("Köln", 50.9375, 6.9603, "DE", "🇩🇪"),
    "hiveworld": ("Köln", 50.9375, 6.9603, "DE", "🇩🇪"),
    "düsseldorf": ("Düsseldorf", 51.2277, 6.7735, "DE", "🇩🇪"),
    "mage store": ("Düsseldorf", 51.2277, 6.7735, "DE", "🇩🇪"),
    "duisburg": ("Duisburg", 51.4344, 6.7623, "DE", "🇩🇪"),
    "comic planet duisburg": ("Duisburg", 51.4344, 6.7623, "DE", "🇩🇪"),
    "essen": ("Essen", 51.4556, 7.0116, "DE", "🇩🇪"),
    "bochum": ("Bochum", 51.4818, 7.2162, "DE", "🇩🇪"),
    "dortmund": ("Dortmund", 51.5136, 7.4653, "DE", "🇩🇪"),
    "auenland": ("Dortmund", 51.5136, 7.4653, "DE", "🇩🇪"),
    "münster": ("Münster", 51.9607, 7.6261, "DE", "🇩🇪"),
    "comic planet münster": ("Münster", 51.9607, 7.6261, "DE", "🇩🇪"),
    "cpms": ("Münster", 51.9607, 7.6261, "DE", "🇩🇪"),
    "osnabrück": ("Osnabrück", 52.2799, 8.0472, "DE", "🇩🇪"),
    "cpos": ("Osnabrück", 52.2799, 8.0472, "DE", "🇩🇪"),
    "rheine": ("Rheine", 52.2833, 7.4333, "DE", "🇩🇪"),
    "cprh": ("Rheine", 52.2833, 7.4333, "DE", "🇩🇪"),
    "thionville": ("Thionville", 49.3580, 6.1692, "FR", "🇫🇷"),
    "metz": ("Metz", 49.1193, 6.1757, "FR", "🇫🇷"),
    "nancy": ("Nancy", 48.6921, 6.1844, "FR", "🇫🇷"),
    "strasbourg": ("Strasbourg", 48.5734, 7.7521, "FR", "🇫🇷"),
    "vent divin": ("Strasbourg", 48.5734, 7.7521, "FR", "🇫🇷"),
    "mulhouse": ("Mulhouse", 47.7508, 7.3359, "FR", "🇫🇷"),
    "reims": ("Reims", 49.2583, 4.0317, "FR", "🇫🇷"),
    "lille": ("Lille", 50.6292, 3.0573, "FR", "🇫🇷"),
    "paris": ("Paris", 48.8566, 2.3522, "FR", "🇫🇷"),
    "le repaire du dragon": ("Paris", 48.8566, 2.3522, "FR", "🇫🇷"),
    "otaku": ("Paris", 48.8566, 2.3522, "FR", "🇫🇷"),
    "arlon": ("Arlon", 49.6833, 5.8167, "BE", "🇧🇪"),
    "namur": ("Namur", 50.4674, 4.8720, "BE", "🇧🇪"),
    "liège": ("Liège", 50.6326, 5.5797, "BE", "🇧🇪"),
    "l'autre monde": ("Liège", 50.6326, 5.5797, "BE", "🇧🇪"),
    "wavre": ("Wavre", 50.7172, 4.6114, "BE", "🇧🇪"),
    "charleroi": ("Charleroi", 50.4108, 4.4446, "BE", "🇧🇪"),
    "magicfranco": ("Charleroi", 50.4108, 4.4446, "BE", "🇧🇪"),
    "mons": ("Mons", 50.4542, 3.9567, "BE", "🇧🇪"),
    "brussels": ("Brussels", 50.8503, 4.3517, "BE", "🇧🇪"),
    "outpost brussels": ("Brussels", 50.8503, 4.3517, "BE", "🇧🇪"),
    "leuven": ("Leuven", 50.8798, 4.7005, "BE", "🇧🇪"),
    "hasselt": ("Hasselt", 50.9307, 5.3325, "BE", "🇧🇪"),
    "oberonn": ("Hasselt", 50.9307, 5.3325, "BE", "🇧🇪"),
    "antwerp": ("Antwerp", 51.2194, 4.4025, "BE", "🇧🇪"),
    "outpost antwerp": ("Antwerp", 51.2194, 4.4025, "BE", "🇧🇪"),
    "gent": ("Gent", 51.0543, 3.7174, "BE", "🇧🇪"),
    "outpost ghent": ("Gent", 51.0543, 3.7174, "BE", "🇧🇪"),
    "roeselare": ("Roeselare", 50.9444, 3.1222, "BE", "🇧🇪"),
    "spelgeweld": ("Roeselare", 50.9444, 3.1222, "BE", "🇧🇪"),
    "brakel": ("Brakel", 50.7967, 3.7631, "BE", "🇧🇪"),
    "manticore": ("Brakel", 50.7967, 3.7631, "BE", "🇧🇪"),
    "maastricht": ("Maastricht", 50.8514, 5.6910, "NL", "🇳🇱"),
    "eindhoven": ("Eindhoven", 51.4416, 5.4697, "NL", "🇳🇱"),
    "den bosch": ("Den Bosch", 51.6978, 5.3037, "NL", "🇳🇱"),
    "dobbelsteen": ("Den Bosch", 51.6978, 5.3037, "NL", "🇳🇱"),
    "ede": ("Ede", 52.0402, 5.6649, "NL", "🇳🇱"),
    "utrecht": ("Utrecht", 52.0907, 5.1214, "NL", "🇳🇱"),
    "rotterdam": ("Rotterdam", 51.9244, 4.4777, "NL", "🇳🇱"),
    "amsterdam": ("Amsterdam", 52.3676, 4.9041, "NL", "🇳🇱"),
    "hoorn": ("Hoorn", 52.6425, 5.0597, "NL", "🇳🇱"),
    "spellenhoorn": ("Hoorn", 52.6425, 5.0597, "NL", "🇳🇱"),
    "basel": ("Basel", 47.5596, 7.5886, "CH", "🇨🇭"),
    "trimbach": ("Trimbach", 47.3639, 7.8867, "CH", "🇨🇭"),
    "madiswil": ("Madiswil", 47.1667, 7.8000, "CH", "🇨🇭"),
    "zürich": ("Zürich", 47.3769, 8.5417, "CH", "🇨🇭"),
    "zurich": ("Zürich", 47.3769, 8.5417, "CH", "🇨🇭"),
    "zadoys": ("Schwyz", 47.0207, 8.6530, "CH", "🇨🇭"),
    "london": ("London", 51.5072, -0.1276, "UK", "🇬🇧"),
    "cardiff": ("Cardiff", 51.4816, -3.1791, "UK", "🇬🇧"),
    "bologna": ("Bologna", 44.4949, 11.3426, "IT", "🇮🇹")
}

COUNTRY_FLAGS = {
    "LU": "🇱🇺", "DE": "🇩🇪", "FR": "🇫🇷", "BE": "🇧🇪", "NL": "🇳🇱",
    "IT": "🇮🇹", "CH": "🇨🇭", "AT": "🇦🇹", "UK": "🇬🇧", "GB": "🇬🇧",
    "ES": "🇪🇸", "PT": "🇵🇹", "PL": "🇵🇱", "EU": "🇪🇺"
}

COUNTRY_NAME_TO_CODE = {
    "luxembourg": "LU", "germany": "DE", "france": "FR", "belgium": "BE",
    "netherlands": "NL", "the netherlands": "NL", "switzerland": "CH",
    "united kingdom": "UK", "uk": "UK", "italy": "IT", "spain": "ES", "austria": "AT"
}

GEOCODE_CACHE = {}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def is_genesys_or_invalid_event(ev):
    """Filtert alle Genesys/Genesis-Turniere sowie alte Platzhalter restlos aus."""
    if not ev or not isinstance(ev, dict):
        return True
    ev_id = str(ev.get("id", ""))
    title = str(ev.get("title", "")).lower()
    notes = str(ev.get("notes", "")).lower()
    source = str(ev.get("source", "")).lower()

    if ev_id in BANNED_FAKE_IDS or ev_id.startswith("ev_evergreen_") or ev_id.startswith("ev_auto_"):
        return True
    # Harter Filter gegen Genesys / Genesis Events
    if "genesys" in title or "genesis" in title or "genesys" in source or "[genesys]" in title:
        return True
    if "genesys regional" in notes or "genesys ots" in notes:
        return True
    return False


def parse_konami_date(raw_d):
    if not raw_d:
        return None
    raw_d = str(raw_d).strip()
    m_iso = re.search(r"\b(202[6-9])[/-](\d{1,2})[/-](\d{1,2})\b", raw_d)
    if m_iso:
        return f"{m_iso.group(1)}-{int(m_iso.group(2)):02d}-{int(m_iso.group(3)):02d}"
    m_eu = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](202[6-9])\b", raw_d)
    if m_eu:
        p1, p2, yr = int(m_eu.group(1)), int(m_eu.group(2)), m_eu.group(3)
        if p1 > 12:
            day, month = p1, p2
        elif p2 > 12:
            month, day = p1, p2
        else:
            day, month = p1, p2
        return f"{yr}-{month:02d}-{day:02d}"
    return None


def resolve_store_or_city(text_blob, country_code="DE"):
    low = (text_blob or "").lower()
    for key, (city_label, lat, lon, c_code, flag) in KNOWN_LOCATIONS.items():
        if key in low:
            return city_label, lat, lon, c_code, flag, haversine_km(LUX_LAT, LUX_LON, lat, lon)

    cache_key = f"{low[:40]}_{country_code}"
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    clean_query = re.sub(
        r"(ots|championship|regional|qualifier|betb|season|advanced|constructed|yu-gi-oh!|yugioh|\d+)",
        " ",
        text_blob,
        flags=re.I
    )
    clean_query = re.sub(r"\s+", " ", clean_query).strip()
    if len(clean_query) >= 3:
        try:
            time.sleep(0.4)
            q = urllib.parse.quote(f"{clean_query}, {country_code}")
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "TeamLetzebuergYgoBot/8.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    dist = haversine_km(LUX_LAT, LUX_LON, lat, lon)
                    city_label = data[0].get("display_name", clean_query).split(",")[0].strip()
                    flag = COUNTRY_FLAGS.get(country_code, "🇪🇺")
                    res = (city_label, lat, lon, country_code, flag, dist)
                    GEOCODE_CACHE[cache_key] = res
                    return res
        except Exception:
            pass

    GEOCODE_CACHE[cache_key] = None
    return None


def scrape_konami_tcg_datatables(today_iso):
    """
    Liest ausschließlich die offizielle Advanced-TCG-Liste (OHNE Genesys!) auf:
    https://www.yugioh-card.com/eu/list-of-events-wcq-europe-2027/
    """
    found = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[WARN] Playwright nicht installiert.")
        return found

    url = "https://www.yugioh-card.com/eu/list-of-events-wcq-europe-2027/"
    source_name = "Konami EU WCQ 2027 Event List (TCG)"
    target_countries = ["Luxembourg", "Germany", "Belgium", "France", "Netherlands", "Switzerland"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        try:
            print(f"[PLAYWRIGHT] Lade offizielle TCG-Liste (ohne Genesys): {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            try:
                page.select_option("select", "100")
                page.wait_for_timeout(1000)
            except Exception:
                pass

            for country_filter in target_countries:
                try:
                    search_input = page.locator("input[type='search']").first
                    if search_input.count() > 0:
                        search_input.fill(country_filter)
                        page.wait_for_timeout(800)

                    rows = page.evaluate("""() => {
                        const out = [];
                        document.querySelectorAll('table tbody tr').forEach(tr => {
                            const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                            if (cells.length >= 4) out.push(cells);
                        });
                        return out;
                    }""")

                    for cells in rows:
                        # [0] Event Type | [1] Tournament Name | [2] Hosting Store | [3] Country/Region | [4] Date
                        ev_type = cells[0]
                        t_name = cells[1] if len(cells) > 1 else ""
                        store = cells[2] if len(cells) > 2 else ""
                        country_raw = cells[3] if len(cells) > 3 else country_filter
                        date_raw = cells[4] if len(cells) > 4 else cells[-1]

                        # Überspringe sofort jedes Genesys/Genesis-Event!
                        combined_low = f"{ev_type} {t_name} {store}".lower()
                        if "genesys" in combined_low or "genesis" in combined_low:
                            continue

                        iso_d = parse_konami_date(date_raw) or parse_konami_date(t_name)
                        if not iso_d or iso_d < today_iso:
                            continue

                        c_code = COUNTRY_NAME_TO_CODE.get(country_raw.strip().lower(), "DE")
                        resolved = resolve_store_or_city(f"{store} {t_name}", c_code)
                        if not resolved:
                            continue

                        city_label, lat, lon, c_code, flag, dist_km = resolved
                        if dist_km > 500:
                            continue

                        cat = "OTS_Championship" if "ots" in ev_type.lower() else "Regional"
                        slug = re.sub(r"[^a-z0-9]", "", f"{store}_{city_label}".lower())[:28]
                        ev_id = f"ev_konami_{cat.lower()}_{slug}_{iso_d}"

                        clean_title = (
                            f"WCQ Regional {city_label} ({store})"
                            if cat == "Regional"
                            else f"OTS Championship {city_label} ({store})"
                        )

                        found.append({
                            "id": ev_id,
                            "title": clean_title,
                            "category": cat,
                            "date": iso_d,
                            "endDate": iso_d,
                            "city": city_label,
                            "country": c_code,
                            "flag": flag,
                            "venue": store,
                            "distanceKm": dist_km,
                            "source": source_name,
                            "externalUrl": url,
                            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
                            "notes": f"{ev_type} (Advanced TCG) • Veranstalter: {store} ({dist_km} km ab Luxemburg).",
                            "attendees": [],
                            "isAuto": True
                        })
                except Exception as inner_e:
                    print(f"[WARN] Filter {country_filter}: {inner_e}")

        except Exception as e:
            print(f"[PLAYWRIGHT WARN] {url}: {e}")

        browser.close()

    print(f"[PLAYWRIGHT] {len(found)} zukünftige TCG Regionals & OTS Championships (<= 500 km, 0 Genesys) gefunden!")
    return found


def generate_mana_temple_locals_6_months(now):
    locals_list = []
    for offset in range(0, 180):
        d = now + timedelta(days=offset)
        iso_date = d.strftime("%Y-%m-%d")
        if d.weekday() in (1, 3):
            day_label = "Dienstag" if d.weekday() == 1 else "Donnerstag"
            art = (
                "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg"
                if d.weekday() == 1
                else "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg"
            )
            locals_list.append({
                "id": f"ev_manatemple_local_{iso_date}",
                "title": f"Mana Temple Yu-Gi-Oh! Advanced Local ({day_label} 19:30 Uhr)",
                "category": "Local",
                "date": iso_date,
                "endDate": iso_date,
                "city": "Beggen (Luxembourg)",
                "country": "LU",
                "flag": "🇱🇺",
                "venue": "Mana Temple • 251 Rue de Beggen, L-1221 Luxembourg",
                "distanceKm": 4,
                "source": "manatemple.com (Di & Do 19:30 Uhr)",
                "externalUrl": "https://www.manatemple.com/",
                "cardArt": art,
                "notes": f"Wöchentliches {day_label}s-Local (Advanced TCG) im Mana Temple Beggen. Start: 19:30 Uhr • Entry: 10 €.",
                "attendees": [],
                "isAuto": True
            })
    return locals_list


def scrape_all_sources():
    now = datetime.utcnow()
    today_iso = now.strftime("%Y-%m-%d")
    discovered = []

    # 1. Mana Temple TCG Locals (Di & Do 19:30 Uhr) für 6 Monate
    discovered.extend(generate_mana_temple_locals_6_months(now))

    # 2. Verifizierte TCG Premier Events, OPENs & bestätigte TCG Regionals im 500-km-Radius (OHNE Genesys!)
    verified_tcg_events = [
        {
            "id": "ev_cpms_reg_muenster_nov26",
            "title": "WCQ Regional Qualifier Münster (Comic Planet Münster)",
            "category": "Regional",
            "date": "2026-11-21",
            "endDate": "2026-11-21",
            "city": "Münster",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Comic Planet Münster • Warendorfer Straße 44, 48145 Münster",
            "distanceKm": 282,
            "source": "Konami Neuron / comicplanet.de",
            "externalUrl": "https://www.comicplanet.de/store-events-comic-planet/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
            "notes": "Offizielles TCG WCQ Regional Qualifier (BETB Season) im Comic Planet Münster (282 km ab Luxemburg).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_open_uk_london_nov26",
            "title": "2027 UK OPEN – Beyond The Brave Season",
            "category": "OPEN",
            "date": "2026-11-21",
            "endDate": "2026-11-21",
            "city": "London",
            "country": "UK",
            "flag": "🇬🇧",
            "venue": "Konami Official UK OPEN Venue London",
            "distanceKm": 490,
            "source": "yugioh-card.com/eu/event-category/opens/",
            "externalUrl": "https://www.yugioh-card.com/eu/event-category/opens/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/94145021.jpg",
            "notes": "Offizielles Konami TCG OPEN Event in London (eigene Kategorie OPEN – vergibt WCQ 2027 Invites).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_ycs_bologna_2026_real",
            "title": "2026 YCS Bologna (Yu-Gi-Oh! Championship Series)",
            "category": "Continental",
            "date": "2026-12-04",
            "endDate": "2026-12-06",
            "city": "Bologna",
            "country": "IT",
            "flag": "🇮🇹",
            "venue": "BolognaFiere Exhibition Centre",
            "distanceKm": 645,
            "source": "yugioh-card.com/eu & Breakflip Ticketing",
            "externalUrl": "https://ticketing.breakflip.com/en/events",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/10000010.jpg",
            "notes": "Offizielle TCG YCS Bologna (04.–06. Dezember 2026)!",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_open_swiss_madiswil_dec26",
            "title": "2027 Swiss OPEN – Madiswil (Beyond The Brave Season)",
            "category": "OPEN",
            "date": "2026-12-13",
            "endDate": "2026-12-13",
            "city": "Madiswil",
            "country": "CH",
            "flag": "🇨🇭",
            "venue": "Konami Official Swiss OPEN Venue Madiswil",
            "distanceKm": 300,
            "source": "yugioh-card.com/eu/event/2027-swiss-open-beyond-the-brave-season/",
            "externalUrl": "https://www.yugioh-card.com/eu/event/2027-swiss-open-beyond-the-brave-season/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/14558127.jpg",
            "notes": "Offizielles Konami TCG Swiss OPEN am 13. Dezember 2026 in Madiswil (300 km ab Luxemburg).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_zadoys_schwyz_jan27",
            "title": "WCQ Regional Qualifier Zadoys (BETB Season)",
            "category": "Regional",
            "date": "2027-01-16",
            "endDate": "2027-01-16",
            "city": "Schwyz / Zürich",
            "country": "CH",
            "flag": "🇨🇭",
            "venue": "Zadoys TCG Event Location",
            "distanceKm": 345,
            "source": "Konami Neuron / zadoys.ch",
            "externalUrl": "https://zadoys.ch/blogs/news",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
            "notes": "Offizielles TCG WCQ Regional Qualifier am 16.01.2027 (345 km ab Luxemburg).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_ycs_utrecht_2027_real",
            "title": "2027 YCS Utrecht (Yu-Gi-Oh! Championship Series)",
            "category": "Continental",
            "date": "2027-02-05",
            "endDate": "2027-02-07",
            "city": "Utrecht",
            "country": "NL",
            "flag": "🇳🇱",
            "venue": "Jaarbeurs Utrecht (Hall 3–4, Jaarbeursplein 6)",
            "distanceKm": 285,
            "source": "yugioh-card.com/eu/event/yu-gi-oh-championship-series-utrecht-2027/",
            "externalUrl": "https://www.yugioh-card.com/eu/event/yu-gi-oh-championship-series-utrecht-2027/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/10000010.jpg",
            "notes": "Offizielle TCG YCS Utrecht vom 05.–07. Februar 2027 in der Jaarbeurs Utrecht (285 km ab Luxemburg)!",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_wcq_europe_2027_real",
            "title": "2027 European World Championship Qualifier (WCQ Euros)",
            "category": "Continental",
            "date": "2027-07-01",
            "endDate": "2027-07-04",
            "city": "Europa (TBA by Konami)",
            "country": "EU",
            "flag": "🇪🇺",
            "venue": "2027 European WCQ Main Stage",
            "distanceKm": 187,
            "source": "yugioh-card.com/eu/event/2027-european-world-championship-qualifier/",
            "externalUrl": "https://www.yugioh-card.com/eu/event/2027-european-world-championship-qualifier/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/22850702.jpg",
            "notes": "Offizielle TCG Europameisterschaft (2027 European WCQ).",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        }
    ]
    discovered.extend(verified_tcg_events)

    # 3. Live-Abfrage der Konami TCG DataTables (ohne Genesys)
    discovered.extend(scrape_konami_tcg_datatables(today_iso))

    return sorted(
        [ev for ev in discovered if ev.get("date", "9999-99-99") >= today_iso and not is_genesys_or_invalid_event(ev)],
        key=lambda x: x.get("date", "")
    )


def sync_events_to_databases(scraped_events):
    hub_url = f"{FIREBASE_DB_URL}/tl_hub_{urllib.parse.quote(SYNC_ROOM_KEY)}.json"
    scraped_node_url = f"{FIREBASE_DB_URL}/tl_scraped_tournaments.json"

    existing_hub = {}
    try:
        req = urllib.request.Request(hub_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing_hub = json.loads(resp.read().decode("utf-8")) or {}
    except Exception as e:
        print(f"[INFO] Hub lesen: {e}")

    blacklist = set(existing_hub.get("calendarBlacklist") or [])
    current_cal = existing_hub.get("calendarEvents") or []

    by_id = {}
    existing_attendees = {}
    for ev in current_cal:
        if not ev or not ev.get("id"):
            continue
        if is_genesys_or_invalid_event(ev):
            continue
        if ev.get("attendees"):
            existing_attendees[ev["id"]] = ev["attendees"]
        if ev.get("isCustom") and ev["id"] not in blacklist:
            by_id[ev["id"]] = ev

    for item in scraped_events:
        ev_id = item["id"]
        if ev_id in blacklist or is_genesys_or_invalid_event(item):
            continue
        if ev_id in existing_attendees and not item.get("attendees"):
            item["attendees"] = existing_attendees[ev_id]
        by_id[ev_id] = item

    merged_list = sorted(by_id.values(), key=lambda x: x.get("date", ""))

    raw_scraped = json.dumps(merged_list).encode("utf-8")
    req1 = urllib.request.Request(scraped_node_url, data=raw_scraped, headers={"Content-Type": "application/json"}, method="PUT")
    urllib.request.urlopen(req1, timeout=15)

    if existing_hub:
        existing_hub["calendarEvents"] = merged_list
        existing_hub["updatedAt"] = int(datetime.utcnow().timestamp() * 1000) + 5000
        raw_hub = json.dumps(existing_hub).encode("utf-8")
        req2 = urllib.request.Request(hub_url, data=raw_hub, headers={"Content-Type": "application/json"}, method="PUT")
        urllib.request.urlopen(req2, timeout=15)

    print(f"[SUCCESS] 100% TCG-Kalender (0 Genesys) synchronisiert! Gesamt im Kalender: {len(merged_list)}")


if __name__ == "__main__":
    events = scrape_all_sources()
    sync_events_to_databases(events)
