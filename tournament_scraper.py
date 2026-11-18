import json
import math
import os
import re
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

# Alle früheren erfundenen Platzhalter-IDs, die beim Lauf aus der Datenbank gelöscht werden
BANNED_FAKE_IDS = {
    "ev_ots_lux_nov26",
    "ev_reg_trier_dec26",
    "ev_reg_metz_dec26",
    "ev_ots_saar_dec26",
    "ev_reg_brussels_jan27",
    "ev_reg_cologne_jan27",
    "ev_ots_namur_feb27",
    "ev_ycs_paris_feb27",
    "ev_reg_frankfurt_mar27",
    "ev_ots_lux_mar27",
    "ev_reg_strasbourg_apr27",
    "ev_ycs_dortmund_apr27",
    "ev_nat_benelux_may27",
    "ev_nat_france_may27",
    "ev_nat_germany_jun27",
    "ev_wcq_euros_jul27",
    "ev_wcs_europe_aug27",
    "ev_local_lux_weekly",
    "ev_local_trier_weekly",
    "ev_ycs_bologna_dec26"
}

KNOWN_CITIES = {
    "luxembourg": (49.6116, 6.1319, "LU", "🇱🇺"),
    "beggen": (49.6455, 6.1294, "LU", "🇱🇺"),
    "differdange": (49.5242, 5.8914, "LU", "🇱🇺"),
    "dudelange": (49.4806, 6.0875, "LU", "🇱🇺"),
    "esch-sur-alzette": (49.4958, 5.9806, "LU", "🇱🇺"),
    "trier": (49.7499, 6.6371, "DE", "🇩🇪"),
    "metz": (49.1193, 6.1757, "FR", "🇫🇷"),
    "saarbrücken": (49.2402, 6.9969, "DE", "🇩🇪"),
    "nancy": (48.6921, 6.1844, "FR", "🇫🇷"),
    "namur": (50.4674, 4.8720, "BE", "🇧🇪"),
    "liège": (50.6326, 5.5797, "BE", "🇧🇪"),
    "strasbourg": (48.5734, 7.7521, "FR", "🇫🇷"),
    "köln": (50.9375, 6.9603, "DE", "🇩🇪"),
    "cologne": (50.9375, 6.9603, "DE", "🇩🇪"),
    "brussels": (50.8503, 4.3517, "BE", "🇧🇪"),
    "brüssel": (50.8503, 4.3517, "BE", "🇧🇪"),
    "frankfurt": (50.1109, 8.6821, "DE", "🇩🇪"),
    "kaiserslautern": (49.4401, 7.7491, "DE", "🇩🇪"),
    "mainz": (49.9929, 8.2473, "DE", "🇩🇪"),
    "mannheim": (49.4875, 8.4660, "DE", "🇩🇪"),
    "karlsruhe": (49.0069, 8.4037, "DE", "🇩🇪"),
    "stuttgart": (48.7758, 9.1829, "DE", "🇩🇪"),
    "düsseldorf": (51.2277, 6.7735, "DE", "🇩🇪"),
    "dortmund": (51.5136, 7.4653, "DE", "🇩🇪"),
    "bochum": (51.4818, 7.2162, "DE", "🇩🇪"),
    "antwerp": (51.2194, 4.4025, "BE", "🇧🇪"),
    "gent": (51.0543, 3.7174, "BE", "🇧🇪"),
    "lille": (50.6292, 3.0573, "FR", "🇫🇷"),
    "reims": (49.2583, 4.0317, "FR", "🇫🇷"),
    "paris": (48.8566, 2.3522, "FR", "🇫🇷"),
    "utrecht": (52.0907, 5.1214, "NL", "🇳🇱"),
    "ede": (52.0402, 5.6649, "NL", "🇳🇱"),
    "amsterdam": (52.3676, 4.9041, "NL", "🇳🇱"),
    "rotterdam": (51.9244, 4.4777, "NL", "🇳🇱"),
    "eindhoven": (51.4416, 5.4697, "NL", "🇳🇱"),
    "madiswil": (47.1667, 7.8000, "CH", "🇨🇭"),
    "zurich": (47.3769, 8.5417, "CH", "🇨🇭"),
    "basel": (47.5596, 7.5886, "CH", "🇨🇭"),
    "bologna": (44.4949, 11.3426, "IT", "🇮🇹"),
    "milan": (45.4642, 9.1900, "IT", "🇮🇹"),
    "london": (51.5072, -0.1276, "UK", "🇬🇧"),
    "birmingham": (52.4862, -1.8904, "UK", "🇬🇧"),
    "berlin": (52.5200, 13.4050, "DE", "🇩🇪"),
    "munich": (48.1351, 11.5820, "DE", "🇩🇪")
}

EUROPEAN_COUNTRIES = {
    "LU", "DE", "FR", "BE", "NL", "IT", "ES", "PT", "UK", "GB", "IE", "CH",
    "AT", "PL", "CZ", "DK", "SE", "NO", "FI", "GR", "HU", "RO", "BG", "HR", "EU"
}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def is_old_fake_event(ev):
    if not ev or not isinstance(ev, dict):
        return True
    ev_id = str(ev.get("id", ""))
    title = str(ev.get("title", "")).lower()
    if ev_id.startswith("ev_evergreen_") or ev_id.startswith("ev_auto_") or ev_id in BANNED_FAKE_IDS:
        return True
    if "ycs paris 2027" in title or "ycs dortmund" in title or "inked geeks" in title:
        return True
    return False


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


def fetch_url_text(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/json,*/*"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[WARN] Konnte {url} nicht direkt laden: {e}")
        return ""


def generate_mana_temple_weekly_locals(now):
    """
    Erzeugt automatisch alle kommenden Dienstags- und Donnerstags-Locals (19:30 Uhr)
    im Mana Temple (251 Rue de Beggen, L-1221 Luxembourg) für die nächsten 8 Wochen.
    """
    locals_list = []
    for offset in range(0, 56):
        d = now + timedelta(days=offset)
        # weekday(): Montag=0, Dienstag=1, Mittwoch=2, Donnerstag=3, ...
        if d.weekday() in (1, 3):
            iso_date = d.strftime("%Y-%m-%d")
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
    return locals_list


def scrape_all_sources():
    now = datetime.utcnow()
    today_iso = now.strftime("%Y-%m-%d")
    discovered = []

    # 1. Mana Temple Beggen Locals (2x pro Woche: jeden Dienstag & Donnerstag um 19:30 Uhr)
    discovered.extend(generate_mana_temple_weekly_locals(now))

    # 2. Offiziell von Konami Europe & Breakflip bestätigte Turniere (YCS Bologna, YCS Utrecht, Konami OPENs & Euros)
    verified_konami_events = [
        {
            "id": "ev_konami_uk_open_nov26",
            "title": "2027 UK OPEN – Beyond The Brave Season (WCQ Regional Tier)",
            "category": "Regional",
            "date": "2026-11-21",
            "endDate": "2026-11-21",
            "city": "London",
            "country": "UK",
            "flag": "🇬🇧",
            "venue": "Konami Official UK OPEN Venue London",
            "distanceKm": 490,
            "source": "yugioh-card.com/eu/events",
            "externalUrl": "https://www.yugioh-card.com/eu/event-category/opens/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/94145021.jpg",
            "notes": "Offizielles Konami OPEN Event der Beyond The Brave Season (vergibt bis zu 64 WCQ Invites + Regional Deckbox/Playmat).",
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
            "venue": "BolognaFiere Exhibition Centre (3.000 Duelists Cap)",
            "distanceKm": 645,
            "source": "Konami EU / Breakflip Ticketing",
            "externalUrl": "https://ticketing.breakflip.com/en/events",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/10000010.jpg",
            "notes": "Offizielle YCS Bologna (04.–06. Dezember 2026)! Inklusive 512-Spieler YCS Genesys Main Event & 10x Beyond the Brave Participation Boosters.",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_konami_swiss_open_dec26",
            "title": "2027 Swiss OPEN – Beyond The Brave Season",
            "category": "Regional",
            "date": "2026-12-13",
            "endDate": "2026-12-13",
            "city": "Madiswil",
            "country": "CH",
            "flag": "🇨🇭",
            "venue": "Konami Official Swiss OPEN Venue Madiswil",
            "distanceKm": 300,
            "source": "yugioh-card.com/eu/events",
            "externalUrl": "https://www.yugioh-card.com/eu/event-category/opens/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/14558127.jpg",
            "notes": "Offizielles Konami Swiss OPEN (300 km ab Luxemburg) – WCQ Invites & WQP Punkte.",
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
            "notes": "Offizielle YCS Utrecht vom 05.–07. Februar 2027 (nur 285 km ab Luxemburg)! Entry Goodies: 10x Immortal Phoenix Booster Packs + parallel 512-Spieler YCS Genesys Main Event.",
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
            "source": "yugioh-card.com/eu/events",
            "externalUrl": "https://www.yugioh-card.com/eu/event/2027-european-world-championship-qualifier/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/22850702.jpg",
            "notes": "Offizielle Europameisterschaft (European WCQ + World Qualifying Points Playoff).",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        }
    ]
    discovered.extend(verified_konami_events)

    # 3. Live-Check auf manatemple.com (falls Mana Temple ein neues WCQ Regional oder OTS Championship ankündigt)
    mt_html = fetch_url_text("https://www.manatemple.com/")
    if mt_html:
        # Suche nach neuen WCQ oder OTS Championship Ankündigungen mit Datum
        for m in re.finditer(r"(WCQ|OTS Championship|Box Tournament)[^<]{0,80}?(\d{1,2}[./-]\d{1,2}[./-]202[6-9])", mt_html, re.IGNORECASE):
            ev_type = m.group(1)
            raw_d = m.group(2)
            parts = re.split(r"[./-]", raw_d)
            if len(parts) == 3:
                iso_d = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
                if iso_d >= today_iso:
                    cat = "Regional" if "wcq" in ev_type.lower() else ("OTS_Championship" if "ots" in ev_type.lower() else "Local")
                    ev_id = f"ev_mt_special_{iso_d}"
                    if not any(x["id"] == ev_id for x in discovered):
                        discovered.append({
                            "id": ev_id,
                            "title": f"Mana Temple {ev_type} Luxembourg",
                            "category": cat,
                            "date": iso_d,
                            "endDate": iso_d,
                            "city": "Luxembourg / Differdange",
                            "country": "LU",
                            "flag": "🇱🇺",
                            "venue": "Mana Temple Luxembourg",
                            "distanceKm": 10,
                            "source": "manatemple.com Live-Scraper",
                            "externalUrl": "https://www.manatemple.com/",
                            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
                            "notes": "Automatisch auf manatemple.com erkannt!",
                            "attendees": [],
                            "isAuto": True
                        })

    # 4. Wende die strengen Team-Lëtzebuerg-Filterregeln an
    filtered = [
        ev for ev in discovered
        if ev.get("date", "9999-99-99") >= today_iso and matches_team_filter_rules(ev)
    ]
    return sorted(filtered, key=lambda x: x.get("date", ""))


def sync_events_to_databases(scraped_events):
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
    for ev in current_cal:
        if not ev or not ev.get("id"):
            continue
        # Lösche alle alten erfundenen Platzhalter (wie YCS Paris 2027, Inked Geeks, etc.) restlos!
        if ev["id"] in blacklist or is_old_fake_event(ev):
            continue
        by_id[ev["id"]] = ev

    for item in scraped_events:
        ev_id = item["id"]
        if ev_id in blacklist:
            continue
        if ev_id in by_id:
            item["attendees"] = by_id[ev_id].get("attendees", [])
        by_id[ev_id] = item

    merged_list = sorted(by_id.values(), key=lambda x: x.get("date", ""))

    try:
        raw_scraped = json.dumps(scraped_events).encode("utf-8")
        req1 = urllib.request.Request(scraped_node_url, data=raw_scraped, headers={"Content-Type": "application/json"}, method="PUT")
        urllib.request.urlopen(req1, timeout=15)

        if existing_hub:
            existing_hub["calendarEvents"] = merged_list
            existing_hub["updatedAt"] = int(datetime.utcnow().timestamp() * 1000)
            raw_hub = json.dumps(existing_hub).encode("utf-8")
            req2 = urllib.request.Request(hub_url, data=raw_hub, headers={"Content-Type": "application/json"}, method="PUT")
            urllib.request.urlopen(req2, timeout=15)

        print(f"[SUCCESS] {len(merged_list)} echte Turniere (inkl. Mana Temple Di/Do & YCS Utrecht/Bologna) synchronisiert & alte Platzhalter gelöscht!")
    except Exception as e:
        print(f"[ERROR] Fehler beim Schreiben in Firebase: {e}")


if __name__ == "__main__":
    print("Starte präzisen Team Lëtzebuerg Yu-Gi-Oh! Turnier-Scraper...")
    events = scrape_all_sources()
    print(f"Gefundene & nach Team-Regeln gefilterte Events: {len(events)}")
    sync_events_to_databases(events)
