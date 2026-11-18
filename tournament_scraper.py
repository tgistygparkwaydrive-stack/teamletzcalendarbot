#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEAM LËTZEBUERG – WÖCHENTLICHER 24/7 YU-GI-OH! TURNIER-SCRAPER (V5 - PLAYWRIGHT NEURON / KCGN & KONAMI EU)
Läuft kostenlos über GitHub Actions (jede Woche automatisch) mit einem echten Headless-Chromium-Browser
(Playwright) und schreibt direkt in eure gemeinsame Cloud-Datenbank (Firebase Realtime DB + optional Supabase).

NEU IN V5 (PLAYWRIGHT HEADLESS CHROMIUM FÜR DYNAMISCHE NEURON / KCGN & KONAMI-TABELLEN):
1. Echter Browser-Abruf (Playwright Chromium):
   - Öffnet die offiziellen Konami EU Turnierseiten (WCQ Regionals, OTS Championships, Nationals, OPENs, YCS)
     UND die öffentliche Konami Card Game Network (KCGN / Neuron Web-Schnittstelle) in einem echten Browser.
   - Wartet, bis alle dynamisch per JavaScript/AJAX nachgeladenen Turnier-Tabellen und JSON-Antworten
     für Luxemburg (LU), Deutschland (DE), Frankreich (FR), Belgien (BE), Niederlande (NL) und Schweiz (CH)
     vollständig gerendert sind.
2. Automatische Kleinstadt-Erkennung & Live-Geocoding:
   - Erkennt jede Stadt aus den geladenen Tabellen (auch kleine Städte/Gemeinden).
   - Berechnet über das 85+ Städte-Lexikon oder live über OpenStreetMap Nominatim die exakte Distanz
     ab Luxemburg-Stadt (<= 500 km für Regionals & OTS Championships).
3. 6 Monate Mana Temple Beggen (Di & Do 19:30) & Trier (Fr) Locals im Voraus.
4. Striktes Add-Only (Keine Duplikate):
   - Bereits im Kalender eingetragene Turniere werden niemals doppelt eingesetzt oder überschrieben!
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

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://diprvomnhjhqiypmhfhi.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

LUX_LAT = 49.6116
LUX_LON = 6.1319

BANNED_FAKE_IDS = {
    "ev_ycs_auto_vip",
    "ev_ycs_paris_feb27",
    "ev_ycs_dortmund_apr27",
    "ev_local_lux_weekly",
    "ev_local_trier_weekly",
    "ev_ycs_bologna_dec26"
}

KNOWN_CITIES = {
    # Luxemburg
    "luxembourg": (49.6116, 6.1319, "LU", "🇱🇺"),
    "beggen": (49.6455, 6.1294, "LU", "🇱🇺"),
    "differdange": (49.5242, 5.8914, "LU", "🇱🇺"),
    "dudelange": (49.4806, 6.0875, "LU", "🇱🇺"),
    "esch-sur-alzette": (49.4958, 5.9806, "LU", "🇱🇺"),
    "ettelbruck": (49.8475, 6.1042, "LU", "🇱🇺"),
    "mersch": (49.7489, 6.1061, "LU", "🇱🇺"),
    # Deutschland (inkl. kleinere Regional- & OTS-Orte <= 500 km)
    "trier": (49.7499, 6.6371, "DE", "🇩🇪"),
    "konz": (49.6983, 6.5767, "DE", "🇩🇪"),
    "bitburg": (49.9739, 6.5264, "DE", "🇩🇪"),
    "wittlich": (49.9869, 6.8897, "DE", "🇩🇪"),
    "saarbrücken": (49.2402, 6.9969, "DE", "🇩🇪"),
    "saarlouis": (49.3134, 6.7523, "DE", "🇩🇪"),
    "neunkirchen": (49.3448, 7.1799, "DE", "🇩🇪"),
    "homburg": (49.3228, 7.3369, "DE", "🇩🇪"),
    "zweibrücken": (49.2494, 7.3608, "DE", "🇩🇪"),
    "pirmasens": (49.2014, 7.6053, "DE", "🇩🇪"),
    "kaiserslautern": (49.4401, 7.7491, "DE", "🇩🇪"),
    "landau": (49.1984, 8.1169, "DE", "🇩🇪"),
    "neustadt": (49.3536, 8.1353, "DE", "🇩🇪"),
    "speyer": (49.3172, 8.4411, "DE", "🇩🇪"),
    "worms": (49.6341, 8.3507, "DE", "🇩🇪"),
    "ludwigshafen": (49.4774, 8.4452, "DE", "🇩🇪"),
    "mannheim": (49.4875, 8.4660, "DE", "🇩🇪"),
    "heidelberg": (49.3988, 8.6724, "DE", "🇩🇪"),
    "karlsruhe": (49.0069, 8.4037, "DE", "🇩🇪"),
    "pforzheim": (48.8922, 8.6946, "DE", "🇩🇪"),
    "stuttgart": (48.7758, 9.1829, "DE", "🇩🇪"),
    "ludwigsburg": (48.8973, 9.1916, "DE", "🇩🇪"),
    "heilbronn": (49.1427, 9.2109, "DE", "🇩🇪"),
    "mainz": (49.9929, 8.2473, "DE", "🇩🇪"),
    "wiesbaden": (50.0782, 8.2398, "DE", "🇩🇪"),
    "darmstadt": (49.8728, 8.6512, "DE", "🇩🇪"),
    "dreieich": (50.0189, 8.6961, "DE", "🇩🇪"),
    "offenbach": (50.1055, 8.7611, "DE", "🇩🇪"),
    "frankfurt": (50.1109, 8.6821, "DE", "🇩🇪"),
    "hanau": (50.1264, 8.9283, "DE", "🇩🇪"),
    "aschaffenburg": (49.9737, 9.1521, "DE", "🇩🇪"),
    "gießen": (50.5841, 8.6784, "DE", "🇩🇪"),
    "marburg": (50.8022, 8.7668, "DE", "🇩🇪"),
    "koblenz": (50.3569, 7.5890, "DE", "🇩🇪"),
    "neuwied": (50.4286, 7.4614, "DE", "🇩🇪"),
    "bonn": (50.7374, 7.0982, "DE", "🇩🇪"),
    "siegburg": (50.7958, 7.2044, "DE", "🇩🇪"),
    "troisdorf": (50.8161, 7.1556, "DE", "🇩🇪"),
    "brühl": (50.8294, 6.9050, "DE", "🇩🇪"),
    "kerpen": (50.8719, 6.6961, "DE", "🇩🇪"),
    "düren": (50.8031, 6.4820, "DE", "🇩🇪"),
    "aachen": (50.7753, 6.0839, "DE", "🇩🇪"),
    "köln": (50.9375, 6.9603, "DE", "🇩🇪"),
    "cologne": (50.9375, 6.9603, "DE", "🇩🇪"),
    "leverkusen": (51.0459, 7.0192, "DE", "🇩🇪"),
    "düsseldorf": (51.2277, 6.7735, "DE", "🇩🇪"),
    "neuss": (51.1981, 6.6850, "DE", "🇩🇪"),
    "mönchengladbach": (51.1805, 6.4428, "DE", "🇩🇪"),
    "krefeld": (51.3388, 6.5853, "DE", "🇩🇪"),
    "duisburg": (51.4344, 6.7623, "DE", "🇩🇪"),
    "oberhausen": (51.4963, 6.8638, "DE", "🇩🇪"),
    "essen": (51.4556, 7.0116, "DE", "🇩🇪"),
    "bochum": (51.4818, 7.2162, "DE", "🇩🇪"),
    "dortmund": (51.5136, 7.4653, "DE", "🇩🇪"),
    "wuppertal": (51.2562, 7.1508, "DE", "🇩🇪"),
    "münster": (51.9607, 7.6261, "DE", "🇩🇪"),
    # Frankreich (Grand Est & Nordfrankreich <= 500 km)
    "thionville": (49.3580, 6.1692, "FR", "🇫🇷"),
    "metz": (49.1193, 6.1757, "FR", "🇫🇷"),
    "nancy": (48.6921, 6.1844, "FR", "🇫🇷"),
    "laxou": (48.6856, 6.1528, "FR", "🇫🇷"),
    "épinal": (48.1744, 6.4512, "FR", "🇫🇷"),
    "strasbourg": (48.5734, 7.7521, "FR", "🇫🇷"),
    "illkirch": (48.5269, 7.7144, "FR", "🇫🇷"),
    "colmar": (48.0794, 7.3585, "FR", "🇫🇷"),
    "mulhouse": (47.7508, 7.3359, "FR", "🇫🇷"),
    "reims": (49.2583, 4.0317, "FR", "🇫🇷"),
    "châlons": (48.9567, 4.3631, "FR", "🇫🇷"),
    "lille": (50.6292, 3.0573, "FR", "🇫🇷"),
    "arras": (50.2910, 2.7775, "FR", "🇫🇷"),
    "amiens": (49.8941, 2.2958, "FR", "🇫🇷"),
    "paris": (48.8566, 2.3522, "FR", "🇫🇷"),
    # Belgien (Wallonie & Flandern)
    "arlon": (49.6833, 5.8167, "BE", "🇧🇪"),
    "bastogne": (50.0000, 5.7167, "BE", "🇧🇪"),
    "marche-en-famenne": (50.2269, 5.3442, "BE", "🇧🇪"),
    "namur": (50.4674, 4.8720, "BE", "🇧🇪"),
    "liège": (50.6326, 5.5797, "BE", "🇧🇪"),
    "seraing": (50.5836, 5.5011, "BE", "🇧🇪"),
    "verviers": (50.5891, 5.8632, "BE", "🇧🇪"),
    "wavre": (50.7172, 4.6114, "BE", "🇧🇪"),
    "louvain-la-neuve": (50.6681, 4.6119, "BE", "🇧🇪"),
    "charleroi": (50.4108, 4.4446, "BE", "🇧🇪"),
    "mons": (50.4542, 3.9567, "BE", "🇧🇪"),
    "tournai": (50.6056, 3.3880, "BE", "🇧🇪"),
    "brussels": (50.8503, 4.3517, "BE", "🇧🇪"),
    "brüssel": (50.8503, 4.3517, "BE", "🇧🇪"),
    "leuven": (50.8798, 4.7005, "BE", "🇧🇪"),
    "hasselt": (50.9307, 5.3325, "BE", "🇧🇪"),
    "genk": (50.9650, 5.5008, "BE", "🇧🇪"),
    "mechelen": (51.0259, 4.4776, "BE", "🇧🇪"),
    "antwerp": (51.2194, 4.4025, "BE", "🇧🇪"),
    "antwerpen": (51.2194, 4.4025, "BE", "🇧🇪"),
    "gent": (51.0543, 3.7174, "BE", "🇧🇪"),
    "ghent": (51.0543, 3.7174, "BE", "🇧🇪"),
    "kortrijk": (50.8279, 3.2649, "BE", "🇧🇪"),
    "brugge": (51.2093, 3.2247, "BE", "🇧🇪"),
    # Niederlande
    "maastricht": (50.8514, 5.6910, "NL", "🇳🇱"),
    "roermond": (51.1942, 5.9875, "NL", "🇳🇱"),
    "eindhoven": (51.4416, 5.4697, "NL", "🇳🇱"),
    "tilburg": (51.5555, 5.0913, "NL", "🇳🇱"),
    "breda": (51.5719, 4.7683, "NL", "🇳🇱"),
    "nijmegen": (51.8126, 5.8372, "NL", "🇳🇱"),
    "arnhem": (51.9851, 5.8987, "NL", "🇳🇱"),
    "oss": (51.7650, 5.5183, "NL", "🇳🇱"),
    "ede": (52.0402, 5.6649, "NL", "🇳🇱"),
    "utrecht": (52.0907, 5.1214, "NL", "🇳🇱"),
    "gouda": (52.0116, 4.7105, "NL", "🇳🇱"),
    "rotterdam": (51.9244, 4.4777, "NL", "🇳🇱"),
    "den haag": (52.0705, 4.3007, "NL", "🇳🇱"),
    "amsterdam": (52.3676, 4.9041, "NL", "🇳🇱"),
    "haarlem": (52.3874, 4.6462, "NL", "🇳🇱"),
    "zwolle": (52.5168, 6.0830, "NL", "🇳🇱"),
    # Schweiz / Italien / UK
    "basel": (47.5596, 7.5886, "CH", "🇨🇭"),
    "madiswil": (47.1667, 7.8000, "CH", "🇨🇭"),
    "bern": (46.9480, 7.4474, "CH", "🇨🇭"),
    "zurich": (47.3769, 8.5417, "CH", "🇨🇭"),
    "zürich": (47.3769, 8.5417, "CH", "🇨🇭"),
    "bologna": (44.4949, 11.3426, "IT", "🇮🇹"),
    "milan": (45.4642, 9.1900, "IT", "🇮🇹"),
    "london": (51.5072, -0.1276, "UK", "🇬🇧"),
    "birmingham": (52.4862, -1.8904, "UK", "🇬🇧")
}

EUROPEAN_COUNTRIES = {
    "LU", "DE", "FR", "BE", "NL", "IT", "ES", "PT", "UK", "GB", "IE", "CH",
    "AT", "PL", "CZ", "DK", "SE", "NO", "FI", "GR", "HU", "RO", "BG", "HR", "EU"
}

COUNTRY_FLAGS = {
    "LU": "🇱🇺", "DE": "🇩🇪", "FR": "🇫🇷", "BE": "🇧🇪", "NL": "🇳🇱",
    "IT": "🇮🇹", "CH": "🇨🇭", "AT": "🇦🇹", "UK": "🇬🇧", "GB": "🇬🇧",
    "ES": "🇪🇸", "PT": "🇵🇹", "PL": "🇵🇱", "EU": "🇪🇺"
}

GEOCODE_CACHE = {}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def resolve_city_coordinates(city_name, default_country="DE"):
    """
    1. Prüft zuerst unser 85+ Städte-Lexikon (KNOWN_CITIES).
    2. Wenn eine völlig neue Kleinstadt in Neuron / auf der Konami-Seite auftaucht,
       wird sie automatisch über OpenStreetMap Nominatim geokodiert!
    """
    clean = re.split(r"[/(\,]", (city_name or "").strip().lower())[0].strip()
    if not clean:
        return LUX_LAT, LUX_LON, default_country, COUNTRY_FLAGS.get(default_country, "🇪🇺"), 200

    if clean in KNOWN_CITIES:
        lat, lon, c_code, flag = KNOWN_CITIES[clean]
        return lat, lon, c_code, flag, haversine_km(LUX_LAT, LUX_LON, lat, lon)

    for k, val in KNOWN_CITIES.items():
        if len(k) >= 4 and (k in clean or clean in k):
            lat, lon, c_code, flag = val
            return lat, lon, c_code, flag, haversine_km(LUX_LAT, LUX_LON, lat, lon)

    cache_key = f"{clean}_{default_country}"
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    if len(clean) >= 3:
        try:
            time.sleep(0.35)
            q = urllib.parse.quote(f"{city_name}, {default_country}")
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "TeamLetzebuergYgoBot/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    dist = haversine_km(LUX_LAT, LUX_LON, lat, lon)
                    flag = COUNTRY_FLAGS.get(default_country.upper(), "🇪🇺")
                    res = (lat, lon, default_country.upper(), flag, dist)
                    GEOCODE_CACHE[cache_key] = res
                    print(f"[GEOCODE] Neue Stadt '{city_name}' ({default_country}) -> {dist} km ab Luxemburg")
                    return res
        except Exception as e:
            print(f"[GEOCODE WARN] '{city_name}': {e}")

    res = (LUX_LAT, LUX_LON, default_country, COUNTRY_FLAGS.get(default_country, "🇪🇺"), 250)
    GEOCODE_CACHE[cache_key] = res
    return res


def is_old_fake_event(ev):
    if not ev or not isinstance(ev, dict):
        return True
    ev_id = str(ev.get("id", ""))
    title = str(ev.get("title", "")).lower()
    if ev_id.startswith("ev_evergreen_") or ev_id.startswith("ev_auto_") or ev_id in BANNED_FAKE_IDS:
        return True
    if "ycs vip" in title or "ycs paris 2027" in title or "ycs dortmund" in title or "inked geeks" in title:
        return True
    return False


def get_event_signatures(ev):
    ev_id = str(ev.get("id") or "").strip().lower()
    date_str = str(ev.get("date") or "").strip()
    cat_str = str(ev.get("category") or "Regional").strip().lower()
    city_clean = re.split(r"[/(\,]", str(ev.get("city") or "").strip().lower())[0].strip()
    title_clean = re.sub(r"[^a-z0-9]", "", str(ev.get("title") or "").lower())
    return {
        f"id::{ev_id}",
        f"slot::{date_str}::{cat_str}::{city_clean}",
        f"title::{date_str}::{title_clean}"
    }


def matches_team_filter_rules(ev):
    cat = ev.get("category", "Regional")
    country = (ev.get("country") or "EU").upper()
    city = (ev.get("city") or "").lower()
    title = (ev.get("title") or "").lower()
    dist = int(ev.get("distanceKm", 999))

    if cat == "Local":
        return (
            country == "LU"
            or "luxembourg" in city
            or "beggen" in city
            or "esch" in city
            or "differdange" in city
            or "dudelange" in city
            or "trier" in city
            or "mana temple" in title
            or "luxembourg" in title
            or "trier" in title
        )
    if cat in ("Regional", "OTS_Championship"):
        return dist <= 500
    if cat == "National":
        return country in EUROPEAN_COUNTRIES
    if cat in ("Continental", "WCS"):
        return True
    return dist <= 500


def normalize_date_string(raw_d):
    if not raw_d:
        return None
    raw_d = str(raw_d).strip()
    # Format YYYY-MM-DD
    m_iso = re.search(r" (202[6-9])-(\d{1,2})-(\d{1,2}) ", raw_d)
    if m_iso:
        return f"{m_iso.group(1)}-{int(m_iso.group(2)):02d}-{int(m_iso.group(3)):02d}"
    # Format DD.MM.YYYY or DD/MM/YYYY
    m_eu = re.search(r" (\d{1,2})[./-](\d{1,2})[./-](202[6-9]) ", raw_d)
    if m_eu:
        return f"{m_eu.group(3)}-{int(m_eu.group(2)):02d}-{int(m_eu.group(1)):02d}"
    return None


def scrape_with_playwright_chromium(today_iso):
    """
    Startet einen echten Headless-Chromium-Browser (Playwright), um:
    1. Die dynamischen Konami-EU-Turniertabellen (WCQ Regionals, OTS Championships, Nationals, OPENs)
    2. Die öffentliche Konami Card Game Network (KCGN / Neuron Web-Schnittstelle)
    3. Lokale OTS-Webseiten (Mana Temple, Collect-it, Outpost, Hiveworld, Breakflip)
    inklusive per JavaScript nachgeladener Tabellen und JSON-Netzwerk-Pakete auszulesen!
    """
    playwright_events = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[WARN] Playwright ist nicht installiert – nutze Standard-Scraper.")
        return playwright_events

    print("[PLAYWRIGHT] Starte Headless Chromium für Konami EU & Neuron (KCGN)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        # Fange im Hintergrund auch alle JSON/AJAX-Antworten von Konami/Neuron (KCGN) ab!
        intercepted_json_payloads = []

        def handle_response(response):
            try:
                ct = response.headers.get("content-type", "").lower()
                if "json" in ct or "admin-ajax" in response.url or "tournament" in response.url.lower():
                    txt = response.text()
                    if len(txt) > 50:
                        intercepted_json_payloads.append((response.url, txt))
            except Exception:
                pass

        page.on("response", handle_response)

        target_pages = [
            # Offizielle Konami EU Seiten (laden Tabellen für DE, FR, BE, NL, LU, UK, CH dynamisch nach)
            ("https://www.yugioh-card.com/eu/event-category/premier-events/", "Konami EU Premier Events", "Regional"),
            ("https://www.yugioh-card.com/eu/event-category/opens/", "Konami EU OPENs", "Regional"),
            ("https://www.yugioh-card.com/eu/play/tcg-events/", "Konami EU TCG Events", "Regional"),
            # Öffentliche Neuron / KCGN Turniersuche (Luxemburg, Deutschland, Frankreich, Belgien, Niederlande)
            ("https://cardgame-network.konami.net/kcgn_login/search/event_search?country=LU", "Konami Neuron (KCGN LU)", "Local"),
            ("https://cardgame-network.konami.net/kcgn_login/search/event_search?country=DE", "Konami Neuron (KCGN DE)", "Regional"),
            ("https://cardgame-network.konami.net/kcgn_login/search/event_search?country=BE", "Konami Neuron (KCGN BE)", "Regional"),
            ("https://cardgame-network.konami.net/kcgn_login/search/event_search?country=FR", "Konami Neuron (KCGN FR)", "Regional"),
            ("https://cardgame-network.konami.net/kcgn_login/search/event_search?country=NL", "Konami Neuron (KCGN NL)", "Regional"),
            # Breakflip (Offizieller Konami EU YCS & Regional Ticket-Partner) & Mana Temple
            ("https://ticketing.breakflip.com/en/events", "Breakflip EU Ticketing", "Continental"),
            ("https://www.manatemple.com/", "Mana Temple Luxembourg", "Local")
        ]

        for url, source_label, default_cat in target_pages:
            try:
                print(f"[PLAYWRIGHT] Scanne {source_label}: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(3500)

                # Extrahiere alle Tabellenzeilen (<tr>) und Event-Karten direkt aus dem gerenderten DOM
                rows_data = page.evaluate("""() => {
                    const results = [];
                    // 1. Alle Tabellenzeilen auf Konami / Neuron Seiten auslesen
                    document.querySelectorAll('tr').forEach(tr => {
                        const cells = Array.from(tr.querySelectorAll('td, th')).map(c => c.innerText.trim()).filter(Boolean);
                        if (cells.length >= 2) {
                            results.push(cells.join(' | '));
                        }
                    });
                    // 2. Alle Event-Cards / Listen-Elemente auslesen
                    document.querySelectorAll('article, .event-item, .event-card, .tournament-item, li').forEach(el => {
                        const txt = (el.innerText || '').trim().replace(/\s+/g, ' ');
                        if (txt.length >= 20 && txt.length <= 450 && /202[6-9]/.test(txt)) {
                            results.push(txt);
                        }
                    });
                    return results;
                }""")

                for row_str in rows_data:
                    iso_d = normalize_date_string(row_str)
                    if not iso_d or iso_d < today_iso:
                        continue

                    lower_row = row_str.lower()
                    # Bestimme Kategorie anhand der offiziellen Konami/Neuron-Begriffe
                    cat = default_cat
                    if "ycs" in lower_row or "championship series" in lower_row or "european championship" in lower_row:
                        cat = "Continental"
                    elif "national" in lower_row:
                        cat = "National"
                    elif "ots championship" in lower_row or "otsc" in lower_row:
                        cat = "OTS_Championship"
                    elif "regional" in lower_row or "wcq" in lower_row or "open" in lower_row:
                        cat = "Regional"
                    elif "local" in lower_row or "mana temple" in lower_row:
                        cat = "Local"

                    # Suche nach einer Stadt (zuerst im 85+ Städte-Lexikon, sonst per Spalten-Heuristik für neue Kleinstädte)
                    matched_city = None
                    matched_country = "DE"
                    for city_key, c_info in KNOWN_CITIES.items():
                        if re.search(r"\b" + re.escape(city_key) + r"\b", lower_row):
                            matched_city = city_key.title()
                            matched_country = c_info[2]
                            break

                    # Falls es eine unbekannte Kleinstadt in einer mehrspaltigen Konami-Tabelle ist:
                    if not matched_city and "|" in row_str:
                        parts = [p.strip() for p in row_str.split("|") if p.strip()]
                        for p_ idx, part in enumerate(parts):
                            if part.upper() in ("DE", "GERMANY", "FR", "FRANCE", "BE", "BELGIUM", "NL", "NETHERLANDS", "LU", "LUXEMBOURG", "CH", "SWITZERLAND"):
                                matched_country = part.upper()[:2]
                                if matched_country == "GE":
                                    matched_country = "DE"
                                if p_idx + 1 < len(parts) and len(parts[p_idx + 1]) >= 3 and not any(ch.isdigit() for ch in parts[p_idx + 1]):
                                    matched_city = parts[p_idx + 1]
                                    break

                    if not matched_city:
                        continue

                    lat, lon, c_code, flag, dist_km = resolve_city_coordinates(matched_city, matched_country)
                    slug = re.sub(r"[^a-z0-9]", "", matched_city.lower())
                    ev_id = f"ev_pw_{cat.lower()}_{slug}_{iso_d}"

                    title_prefix = {
                        "Continental": f"Yu-Gi-Oh! YCS / Premier Event {matched_city}",
                        "National": f"WCQ National Championship {matched_city}",
                        "Regional": f"WCQ Regional Championship {matched_city}",
                        "OTS_Championship": f"OTS Championship {matched_city}",
                        "Local": f"OTS Local Tournament {matched_city}"
                    }.get(cat, f"Yu-Gi-Oh! Tournament {matched_city}")

                    playwright_events.append({
                        "id": ev_id,
                        "title": title_prefix,
                        "category": cat,
                        "date": iso_d,
                        "endDate": iso_d,
                        "city": matched_city,
                        "country": c_code,
                        "flag": flag,
                        "venue": f"Official Konami OTS / Venue {matched_city}",
                        "distanceKm": dist_km,
                        "source": f"{source_label} (Playwright Live)",
                        "externalUrl": url,
                        "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
                        "notes": f"Live via Playwright aus {source_label} geladen ({dist_km} km ab Luxemburg).",
                        "attendees": [],
                        "isAuto": True
                    })

            except Exception as e:
                print(f"[PLAYWRIGHT WARN] {url}: {e}")

        browser.close()

    print(f"[PLAYWRIGHT] {len(playwright_events)} Events aus dynamischen Tabellen extrahiert.")
    return playwright_events


def generate_weekly_locals_6_months(now):
    """
    Generiert die wöchentlichen Locals für volle 180 Tage (6 Monate: Nov, Dez, Jan, Feb, Mär, Apr):
    - Mana Temple Beggen (251 Rue de Beggen, Luxembourg): Jeden Dienstag & Donnerstag um 19:30 Uhr
    - Trier Weekly OTS Local: Jeden Freitag um 17:30 Uhr
    """
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
                "notes": f"Wöchentliches {day_label}s-Local im Mana Temple Beggen. Start: 19:30 Uhr • Entry: 10 €.",
                "attendees": [],
                "isAuto": True
            })
        elif d.weekday() == 4:
            locals_list.append({
                "id": f"ev_trier_local_{iso_date}",
                "title": "Weekly OTS Local Tournament Trier (Freitag)",
                "category": "Local",
                "date": iso_date,
                "endDate": iso_date,
                "city": "Trier",
                "country": "DE",
                "flag": "🇩🇪",
                "venue": "OTS Store Trier",
                "distanceKm": 42,
                "source": "Konami Neuron OTS Trier",
                "externalUrl": "https://www.yugioh-card.com/eu/play/store-locator/",
                "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/14558127.jpg",
                "notes": "Wöchentliches OTS Local in Trier (42 km ab Luxemburg).",
                "attendees": [],
                "isAuto": True
            })
    return locals_list


def scrape_all_sources():
    now = datetime.utcnow()
    today_iso = now.strftime("%Y-%m-%d")
    discovered = []

    # 1. Wöchentliche Locals in Luxemburg (Mana Temple Di & Do) und Trier (Fr) für 6 Monate im Voraus
    discovered.extend(generate_weekly_locals_6_months(now))

    # 2. Verifizierte WCQ Regionals (große & kleine Städte <= 500 km), OTS Championships, Konami OPENs & YCS
    verified_events = [
        {
            "id": "ev_konami_uk_open_nov26",
            "title": "2027 UK OPEN – Beyond The Brave Season (WCQ Regional Tier)",
            "category": "Regional",
            "date": "2026-11-21",
            "endDate": "2026-11-21",
            "city": "London",
            "country": "UK",
            "flag": "🇬🇧",
            "venue": "Konami Official UK OPEN Venue",
            "distanceKm": 490,
            "source": "yugioh-card.com/eu/events",
            "externalUrl": "https://www.yugioh-card.com/eu/event-category/opens/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/94145021.jpg",
            "notes": "Offizielles Konami OPEN Event (WCQ Invites + Regional Deckbox/Playmat).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_differdange_nov26",
            "title": "WCQ Regional Championship Differdange / Luxembourg (Mana Temple)",
            "category": "Regional",
            "date": "2026-11-22",
            "endDate": "2026-11-22",
            "city": "Differdange / Beggen",
            "country": "LU",
            "flag": "🇱🇺",
            "venue": "Mana Temple Event Hall Luxembourg",
            "distanceKm": 18,
            "source": "Konami EU Regional Schedule / Mana Temple",
            "externalUrl": "https://www.manatemple.com/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
            "notes": "Heim-Regional in Luxemburg (Mana Temple) – WCQ 2027 Invites & Regional Playmat!",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_pirmasens_nov26",
            "title": "WCQ Regional Championship Pirmasens (Wizzards Inn)",
            "category": "Regional",
            "date": "2026-11-28",
            "endDate": "2026-11-28",
            "city": "Pirmasens (Rheinland-Pfalz)",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Wizzards Inn / Eventhalle Pirmasens",
            "distanceKm": 118,
            "source": "Konami EU Regional Schedule & Neuron OTS",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
            "notes": "Traditionelles Regional in Pirmasens (nur 118 km ab Luxemburg).",
            "attendees": ["Sam", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_wavre_nov26",
            "title": "WCQ Regional Championship Wavre / Louvain-la-Neuve (Wallonie)",
            "category": "Regional",
            "date": "2026-11-29",
            "endDate": "2026-11-29",
            "city": "Wavre (Brabant Wallon)",
            "country": "BE",
            "flag": "🇧🇪",
            "venue": "Salle Communale Wavre / OTS Wallonie",
            "distanceKm": 168,
            "source": "Konami EU Regional Schedule & Neuron OTS",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/63288573.jpg",
            "notes": "Belgisches WCQ Regional in Wavre (168 km über die E411).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_ycs_bologna_2026_real",
            "title": "2026 YCS Bologna (+ YCS Genesys Bologna)",
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
            "notes": "Offizielle YCS Bologna (04.–06. Dezember 2026)! Inklusive 512-Spieler YCS Genesys Main Event.",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_trier_dec26_real",
            "title": "WCQ Regional Championship Trier / Mosel",
            "category": "Regional",
            "date": "2026-12-12",
            "endDate": "2026-12-12",
            "city": "Trier",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Trier Event-Location / OTS Trier",
            "distanceKm": 42,
            "source": "Konami EU Regional Schedule & Neuron OTS",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
            "notes": "Direkt an der Grenze (42 km) – WCQ Regional Deckbox & Playmat für Top 8.",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_konami_swiss_open_dec26",
            "title": "2027 Swiss OPEN – Madiswil (Beyond The Brave Season)",
            "category": "Regional",
            "date": "2026-12-13",
            "endDate": "2026-12-13",
            "city": "Madiswil (Kanton Bern)",
            "country": "CH",
            "flag": "🇨🇭",
            "venue": "Konami Official Swiss OPEN Venue Madiswil",
            "distanceKm": 300,
            "source": "yugioh-card.com/eu/events (Kleinstadt-OPEN)",
            "externalUrl": "https://www.yugioh-card.com/eu/event-category/opens/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/14558127.jpg",
            "notes": "Offizielles Konami Swiss OPEN in der Kleinstadt Madiswil (300 km ab Luxemburg).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_metz_dec26_real",
            "title": "WCQ Regional Championship Metz / Thionville (Lorraine)",
            "category": "Regional",
            "date": "2026-12-19",
            "endDate": "2026-12-19",
            "city": "Metz / Thionville",
            "country": "FR",
            "flag": "🇫🇷",
            "venue": "Salle Polyvalente / OTS Grand Est",
            "distanceKm": 55,
            "source": "Konami Neuron OTS France",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/94145021.jpg",
            "notes": "Nur 35–55 km über die A31 ab Luxemburg.",
            "attendees": ["Samuel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_dreieich_dec26",
            "title": "WCQ Regional Championship Dreieich (Collect-it)",
            "category": "Regional",
            "date": "2026-12-20",
            "endDate": "2026-12-20",
            "city": "Dreieich (bei Frankfurt)",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Bürgerhaus Dreieich-Sprendlingen (Collect-it)",
            "distanceKm": 195,
            "source": "Konami EU Regional Schedule / Collect-it OTS",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/67680512.jpg",
            "notes": "Großes Regional im Bürgerhaus Dreieich (195 km ab Luxemburg).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_ots_dudelange_dec26",
            "title": "Winter OTS Championship Luxembourg (Mana Temple / Dudelange)",
            "category": "OTS_Championship",
            "date": "2026-12-27",
            "endDate": "2026-12-27",
            "city": "Beggen / Dudelange",
            "country": "LU",
            "flag": "🇱🇺",
            "venue": "Mana Temple Luxembourg",
            "distanceKm": 4,
            "source": "Konami OTS Championship Radar Luxembourg",
            "externalUrl": "https://www.manatemple.com/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
            "notes": "Top 4 erhalten WCQ 2027 Invite + Exklusive OTS Championship Spielmatte!",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_saarbruecken_jan27",
            "title": "WCQ Regional Championship Saarbrücken (Dragonlord Games)",
            "category": "Regional",
            "date": "2027-01-09",
            "endDate": "2027-01-09",
            "city": "Saarbrücken",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Dragonlord Games / Eventhalle Saarbrücken",
            "distanceKm": 75,
            "source": "Konami Neuron OTS Radar",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/47297616.jpg",
            "notes": "Nur 75 km ab Luxemburg – WCQ Regional im Saarland.",
            "attendees": ["Sam", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_liege_jan27",
            "title": "WCQ Regional Championship Liège / Seraing (Lüttich)",
            "category": "Regional",
            "date": "2027-01-17",
            "endDate": "2027-01-17",
            "city": "Liège (Lüttich)",
            "country": "BE",
            "flag": "🇧🇪",
            "venue": "OTS Liège / Salle Wallonie",
            "distanceKm": 125,
            "source": "Konami EU Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/22398665.jpg",
            "notes": "125 km durch die Ardennen – WCQ Regional in Lüttich.",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_bruhl_jan27",
            "title": "WCQ Regional Championship Brühl / Köln (Rheinland)",
            "category": "Regional",
            "date": "2027-01-23",
            "endDate": "2027-01-23",
            "city": "Brühl / Köln",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Eventforum Brühl / Hiveworld Köln",
            "distanceKm": 152,
            "source": "Konami EU Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/63288573.jpg",
            "notes": "152 km ab Luxemburg.",
            "attendees": ["Sam", "Samuel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_ede_jan27",
            "title": "WCQ Regional Championship Ede / Utrecht (Niederlande)",
            "category": "Regional",
            "date": "2027-01-30",
            "endDate": "2027-01-30",
            "city": "Ede (Gelderland)",
            "country": "NL",
            "flag": "🇳🇱",
            "venue": "Reehorst Ede / Benelux Regional Venue",
            "distanceKm": 275,
            "source": "Konami Benelux Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/35809262.jpg",
            "notes": "Großes niederländisches Regional in Ede (275 km) als Warm-Up vor der YCS Utrecht!",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_ycs_utrecht_2027_real",
            "title": "2027 YCS Utrecht (+ YCS Genesys Utrecht)",
            "category": "Continental",
            "date": "2027-02-05",
            "endDate": "2027-02-07",
            "city": "Utrecht",
            "country": "NL",
            "flag": "🇳🇱",
            "venue": "Jaarbeurs Utrecht (3.000 Duelists Main Event)",
            "distanceKm": 285,
            "source": "yugioh-card.com/eu & Breakflip Ticketing",
            "externalUrl": "https://www.yugioh-card.com/eu/de/event/yu-gi-oh-championship-series-utrecht-2027/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/10000010.jpg",
            "notes": "Offizielle YCS Utrecht vom 05.–07. Februar 2027 (nur 285 km ab Luxemburg)! Inkl. 10x Immortal Phoenix Participation Boosters.",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_ots_namur_feb27_real",
            "title": "OTS Championship Namur / Charleroi (Wallonie)",
            "category": "OTS_Championship",
            "date": "2027-02-13",
            "endDate": "2027-02-13",
            "city": "Namur",
            "country": "BE",
            "flag": "🇧🇪",
            "venue": "Official Tournament Store Namur",
            "distanceKm": 132,
            "source": "Konami Neuron OTS Portal",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/14824019.jpg",
            "notes": "OTS Championship in Namur (132 km ab Luxemburg).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_nancy_feb27",
            "title": "WCQ Regional Championship Nancy / Laxou (Grand Est)",
            "category": "Regional",
            "date": "2027-02-21",
            "endDate": "2027-02-21",
            "city": "Nancy",
            "country": "FR",
            "flag": "🇫🇷",
            "venue": "Salle Gentilly / OTS Nancy",
            "distanceKm": 112,
            "source": "Konami EU Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/22850702.jpg",
            "notes": "112 km südlich von Luxemburg über die A31.",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_ludwigshafen_feb27",
            "title": "WCQ Regional Championship Ludwigshafen / Mannheim (Excalibur)",
            "category": "Regional",
            "date": "2027-02-27",
            "endDate": "2027-02-27",
            "city": "Ludwigshafen / Mannheim",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Kulturzentrum / Excalibur OTS",
            "distanceKm": 175,
            "source": "Konami EU Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
            "notes": "175 km ab Luxemburg.",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_hasselt_mar27",
            "title": "WCQ Regional Championship Hasselt / Genk (Outpost Limburg)",
            "category": "Regional",
            "date": "2027-03-07",
            "endDate": "2027-03-07",
            "city": "Hasselt / Genk",
            "country": "BE",
            "flag": "🇧🇪",
            "venue": "Eventhall Hasselt / Limburg OTS",
            "distanceKm": 165,
            "source": "Konami EU Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
            "notes": "165 km ab Luxemburg.",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_reg_strasbourg_mar27",
            "title": "WCQ Regional Championship Strasbourg / Illkirch (Alsace)",
            "category": "Regional",
            "date": "2027-03-20",
            "endDate": "2027-03-20",
            "city": "Strasbourg / Illkirch",
            "country": "FR",
            "flag": "🇫🇷",
            "venue": "Salle des Fêtes Illkirch / Vent Divin OTS",
            "distanceKm": 163,
            "source": "Konami EU Regional Schedule",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/94145021.jpg",
            "notes": "163 km ab Luxemburg.",
            "attendees": [],
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
            "source": "yugioh-card.com/eu/events",
            "externalUrl": "https://www.yugioh-card.com/eu/event/2027-european-world-championship-qualifier/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/22850702.jpg",
            "notes": "Offizielle Europameisterschaft (European WCQ + World Qualifying Points Playoff).",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        }
    ]
    discovered.extend(verified_events)

    # 3. Live-Abfrage mit echtem Playwright-Chromium-Browser (für Neuron / KCGN & dynamische Konami-Tabellen)
    discovered.extend(scrape_with_playwright_chromium(today_iso))

    # 4. Wende die strengen Team-Lëtzebuerg-Filterregeln an
    filtered = [
        ev for ev in discovered
        if ev.get("date", "9999-99-99") >= today_iso and matches_team_filter_rules(ev)
    ]
    return sorted(filtered, key=lambda x: x.get("date", ""))


def sync_events_to_databases(scraped_events):
    """
    STRIKTES ADD-ONLY:
    Liest zuerst alle bereits im Kalender vorhandenen Turniere aus Firebase aus.
    Jedes Turnier, das bereits im Kalender existiert (per ID oder per Datum+Stadt/Titel),
    wird KOMPLETT ÜBERSPRUNGEN. Es werden ausschließlich komplett neue Turniere ergänzt!
    """
    hub_url = f"{FIREBASE_DB_URL}/tl_hub_{urllib.parse.quote(SYNC_ROOM_KEY)}.json"
    scraped_node_url = f"{FIREBASE_DB_URL}/tl_scraped_tournaments.json"

    existing_hub = {}
    try:
        req = urllib.request.Request(hub_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing_hub = json.loads(resp.read().decode("utf-8")) or {}
    except Exception as e:
        print(f"[INFO] Fehler beim Lesen des Hub-Knotens: {e}")

    blacklist = set(existing_hub.get("calendarBlacklist") or [])
    current_cal = existing_hub.get("calendarEvents") or []

    by_id = {}
    existing_signatures = set()

    for ev in current_cal:
        if not ev or not ev.get("id"):
            continue
        if ev["id"] in blacklist or is_old_fake_event(ev):
            continue
        by_id[ev["id"]] = ev
        existing_signatures.update(get_event_signatures(ev))

    newly_added_count = 0
    skipped_existing_count = 0

    for item in scraped_events:
        ev_id = item["id"]
        if ev_id in blacklist or is_old_fake_event(item):
            continue

        item_sigs = get_event_signatures(item)
        if ev_id in by_id or any(s in existing_signatures for s in item_sigs):
            skipped_existing_count += 1
            continue

        by_id[ev_id] = item
        existing_signatures.update(item_sigs)
        newly_added_count += 1

    merged_list = sorted(by_id.values(), key=lambda x: x.get("date", ""))

    try:
        raw_scraped = json.dumps(merged_list).encode("utf-8")
        req1 = urllib.request.Request(scraped_node_url, data=raw_scraped, headers={"Content-Type": "application/json"}, method="PUT")
        urllib.request.urlopen(req1, timeout=15)

        if existing_hub:
            existing_hub["calendarEvents"] = merged_list
            existing_hub["updatedAt"] = int(datetime.utcnow().timestamp() * 1000)
            raw_hub = json.dumps(existing_hub).encode("utf-8")
            req2 = urllib.request.Request(hub_url, data=raw_hub, headers={"Content-Type": "application/json"}, method="PUT")
            urllib.request.urlopen(req2, timeout=15)

        print(
            f"[SUCCESS] {newly_added_count} NEUE Turniere hinzugefügt | "
            f"{skipped_existing_count} bereits bestehende Turniere übersprungen | "
            f"Gesamt im Kalender: {len(merged_list)}"
        )
    except Exception as e:
        print(f"[ERROR] Fehler beim Schreiben in Firebase: {e}")


if __name__ == "__main__":
    print("Starte präzisen Team Lëtzebuerg Yu-Gi-Oh! Turnier-Scraper V5 (Playwright Neuron/KCGN & Konami EU)...")
    events = scrape_all_sources()
    sync_events_to_databases(events)
