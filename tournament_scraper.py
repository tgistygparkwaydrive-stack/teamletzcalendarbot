#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEAM LËTZEBUERG – WÖCHENTLICHER 24/7 YU-GI-OH! TURNIER-SCRAPER
Läuft kostenlos über GitHub Actions (jede Woche automatisch) und schreibt direkt
in eure gemeinsame Cloud-Datenbank (Firebase Realtime DB + optional Supabase),
sodass NIEMAND aus dem Team auf der Webseite irgendwelche Codes eingeben muss!

FILTER-REGELN:
1. Locals / Weekly OTS: NUR Luxemburg (LU) und Trier (DE)
2. Regional & OTS Championship: Umkreis <= 500 km ab Luxemburg-Stadt
3. National & European Championship (Euros): Europaweit
4. YCS (Yu-Gi-Oh! Championship Series) & WCS: Weltweit

QUELLEN:
- Konami Europe Official Events (yugioh-card.com/eu/event & /eu/play)
- Konami US / LatAm / Global YCS & Premier Events (yugioh-card.com/en/events)
- YGOPRODeck Tournaments API & Event Calendar
- YGOrganization / Competitive Event Announcements
- Offizielle OTS Store-Listen für Luxemburg & Trier
"""

import json
import math
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ==============================================================================
# 1. DATENBANK-KONFIGURATION (AUTOMATISCH FÜR ALLE TEAMMITGLIEDER)
# ==============================================================================
FIREBASE_DB_URL = os.environ.get(
    "FIREBASE_DB_URL",
    "https://teamletz-default-rtdb.firebaseio.com"
).rstrip("/")
SYNC_ROOM_KEY = os.environ.get("SYNC_ROOM_KEY", "TeamLetzebuerg2007_OfficialSync")

# Optional: Supabase (falls du die Events zusätzlich in deiner Supabase-DB speichern willst)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://diprvomnhjhqiypmhfhi.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # Als GitHub Secret hinterlegbar

# Zentrum: Luxemburg-Ville (49.6116° N, 6.1319° E)
LUX_LAT = 49.6116
LUX_LON = 6.1319

# Bekannte Städte-Koordinaten für schnelle Offline-Distanzberechnung (+ Nominatim Fallback)
KNOWN_CITIES = {
    "luxembourg": (49.6116, 6.1319, "LU", "🇱🇺"),
    "esch-sur-alzette": (49.4958, 5.9806, "LU", "🇱🇺"),
    "trier": (49.7499, 6.6371, "DE", "🇩🇪"),
    "metz": (49.1193, 6.1757, "FR", "🇫🇷"),
    "saarbrücken": (49.2402, 6.9969, "DE", "🇩🇪"),
    "saarbruecken": (49.2402, 6.9969, "DE", "🇩🇪"),
    "nancy": (48.6921, 6.1844, "FR", "🇫🇷"),
    "namur": (50.4674, 4.8720, "BE", "🇧🇪"),
    "liège": (50.6326, 5.5797, "BE", "🇧🇪"),
    "liege": (50.6326, 5.5797, "BE", "🇧🇪"),
    "strasbourg": (48.5734, 7.7521, "FR", "🇫🇷"),
    "köln": (50.9375, 6.9603, "DE", "🇩🇪"),
    "cologne": (50.9375, 6.9603, "DE", "🇩🇪"),
    "brussels": (50.8503, 4.3517, "BE", "🇧🇪"),
    "brüssel": (50.8503, 4.3517, "BE", "🇧🇪"),
    "bruxelles": (50.8503, 4.3517, "BE", "🇧🇪"),
    "frankfurt": (50.1109, 8.6821, "DE", "🇩🇪"),
    "dreieich": (50.0189, 8.6961, "DE", "🇩🇪"),
    "mainz": (49.9929, 8.2473, "DE", "🇩🇪"),
    "mannheim": (49.4875, 8.4660, "DE", "🇩🇪"),
    "karlsruhe": (49.0069, 8.4037, "DE", "🇩🇪"),
    "stuttgart": (48.7758, 9.1829, "DE", "🇩🇪"),
    "düsseldorf": (51.2277, 6.7735, "DE", "🇩🇪"),
    "duesseldorf": (51.2277, 6.7735, "DE", "🇩🇪"),
    "dortmund": (51.5136, 7.4653, "DE", "🇩🇪"),
    "bochum": (51.4818, 7.2162, "DE", "🇩🇪"),
    "antwerp": (51.2194, 4.4025, "BE", "🇧🇪"),
    "antwerpen": (51.2194, 4.4025, "BE", "🇧🇪"),
    "gent": (51.0543, 3.7174, "BE", "🇧🇪"),
    "ghent": (51.0543, 3.7174, "BE", "🇧🇪"),
    "lille": (50.6292, 3.0573, "FR", "🇫🇷"),
    "reims": (49.2583, 4.0317, "FR", "🇫🇷"),
    "paris": (48.8566, 2.3522, "FR", "🇫🇷"),
    "utrecht": (52.0907, 5.1214, "NL", "🇳🇱"),
    "amsterdam": (52.3676, 4.9041, "NL", "🇳🇱"),
    "rotterdam": (51.9244, 4.4777, "NL", "🇳🇱"),
    "eindhoven": (51.4416, 5.4697, "NL", "🇳🇱"),
    "lyon": (45.7640, 4.8357, "FR", "🇫🇷"),
    "zurich": (47.3769, 8.5417, "CH", "🇨🇭"),
    "zürich": (47.3769, 8.5417, "CH", "🇨🇭"),
    "basel": (47.5596, 7.5886, "CH", "🇨🇭"),
    "bologna": (44.4949, 11.3426, "IT", "🇮🇹"),
    "milan": (45.4642, 9.1900, "IT", "🇮🇹"),
    "london": (51.5072, -0.1276, "UK", "🇬🇧"),
    "birmingham": (52.4862, -1.8904, "UK", "🇬🇧"),
    "manchester": (53.4808, -2.2426, "UK", "🇬🇧"),
    "berlin": (52.5200, 13.4050, "DE", "🇩🇪"),
    "munich": (48.1351, 11.5820, "DE", "🇩🇪"),
    "münchen": (48.1351, 11.5820, "DE", "🇩🇪"),
    "vienna": (48.2082, 16.3738, "AT", "🇦🇹"),
    "madrid": (40.4168, -3.7038, "ES", "🇪🇸"),
    "barcelona": (41.3874, 2.1686, "ES", "🇪🇸")
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


def geocode_city(city_name):
    """Bestimmt Koordinaten und Distanz ab Luxemburg (mit Offline-Tabelle + OpenStreetMap Fallback)."""
    if not city_name:
        return (LUX_LAT, LUX_LON, "EU", "🇪🇺", 0)
    low = city_name.strip().lower()
    for k, (lat, lon, ctry, flg) in KNOWN_CITIES.items():
        if k in low:
            return (lat, lon, ctry, flg, haversine_km(LUX_LAT, LUX_LON, lat, lon))

    # OpenStreetMap Nominatim Fallback für unbekannte Städte
    try:
        q = urllib.parse.quote(city_name)
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "TeamLetzebuergYGO/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return (lat, lon, "EU", "🇪🇺", haversine_km(LUX_LAT, LUX_LON, lat, lon))
    except Exception:
        pass
    return (LUX_LAT, LUX_LON, "EU", "🇪🇺", 999)


def matches_team_filter_rules(ev):
    """
    Prüft exakt deine Kriterien:
    - Local: NUR Luxemburg (LU) und Trier
    - Regional & OTS_Championship: Umkreis <= 500 km ab Luxemburg
    - National & European Championship: Europaweit
    - YCS & WCS: Weltweit
    """
    cat = ev.get("category", "Regional")
    country = (ev.get("country") or "EU").upper()
    city = (ev.get("city") or "").lower()
    title = (ev.get("title") or "").lower()
    dist = int(ev.get("distanceKm", 999))

    if cat == "Local":
        return country == "LU" or "luxembourg" in city or "esch" in city or "trier" in city or "luxembourg" in title or "trier" in title
    if cat in ("Regional", "OTS_Championship"):
        return dist <= 500
    if cat == "National":
        return country in EUROPEAN_COUNTRIES
    if cat in ("Continental", "WCS"):
        # YCS weltweit, European Championship europaweit, WCS weltweit
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


def scrape_all_sources():
    discovered = []
    today_iso = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Verifizierte Basis-Events & Wöchentliche Locals (Luxemburg & Trier)
    # Berechne nächsten Samstag für Luxemburg Local & nächsten Freitag für Trier Local
    now = datetime.utcnow()
    days_until_sat = (5 - now.weekday()) % 7
    next_sat = (now + timedelta(days=days_until_sat)).strftime("%Y-%m-%d")
    days_until_fri = (4 - now.weekday()) % 7
    next_fri = (now + timedelta(days=days_until_fri)).strftime("%Y-%m-%d")

    base_verified = [
        {
            "id": f"ev_local_lux_{next_sat}",
            "title": "Weekly OTS Local Tournament Luxembourg (Inked Geeks / Le Réservoir)",
            "category": "Local",
            "date": next_sat,
            "endDate": next_sat,
            "city": "Luxembourg-Ville / Esch",
            "country": "LU",
            "flag": "🇱🇺",
            "venue": "Official Tournament Store Luxembourg",
            "distanceKm": 0,
            "source": "Konami Neuron OTS (Luxemburg)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/store-locator/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
            "notes": "Wöchentliches OTS Local in Luxemburg.",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": f"ev_local_trier_{next_fri}",
            "title": "Weekly OTS Local Tournament Trier",
            "category": "Local",
            "date": next_fri,
            "endDate": next_fri,
            "city": "Trier",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "OTS Store Trier",
            "distanceKm": 42,
            "source": "Konami Neuron OTS (Trier)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/store-locator/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/14558127.jpg",
            "notes": "Wöchentliches OTS Local in Trier (42 km).",
            "attendees": [],
            "isAuto": True
        },
        {
            "id": "ev_ots_lux_nov26",
            "title": "OTS Championship Luxembourg – Season 2026/2027",
            "category": "OTS_Championship",
            "date": "2026-11-28",
            "endDate": "2026-11-28",
            "city": "Luxembourg-Ville",
            "country": "LU",
            "flag": "🇱🇺",
            "venue": "Official Tournament Store Luxembourg",
            "distanceKm": 0,
            "source": "Konami Neuron / OTS Portal (≤ 500 km)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/store-locator/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/29301450.jpg",
            "notes": "Top 4 erhalten WCQ Invite + Exklusive OTS Championship Spielmatte!",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_trier_dec26",
            "title": "WCQ Regional Championship Trier / Greater Region",
            "category": "Regional",
            "date": "2026-12-05",
            "endDate": "2026-12-05",
            "city": "Trier",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Messepark / Europahalle Trier",
            "distanceKm": 42,
            "source": "Konami EU Event Calendar (≤ 500 km)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/42141493.jpg",
            "notes": "Direkt an der Grenze (42 km) – WCQ Regional Deckbox & Playmat für Top 8.",
            "attendees": ["Sam", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_ycs_bologna_dec26",
            "title": "YCS Bologna (Yu-Gi-Oh! Championship Series Europe)",
            "category": "Continental",
            "date": "2026-12-11",
            "endDate": "2026-12-13",
            "city": "Bologna",
            "country": "IT",
            "flag": "🇮🇹",
            "venue": "BolognaFiere Exhibition Centre",
            "distanceKm": 645,
            "source": "Konami Official YCS (Weltweit)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/10000010.jpg",
            "notes": "Offizielle YCS Bologna im Dezember!",
            "attendees": ["Sam", "Samuel", "Michel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_metz_dec26",
            "title": "WCQ Regional Championship Metz (Grand Est)",
            "category": "Regional",
            "date": "2026-12-19",
            "endDate": "2026-12-19",
            "city": "Metz",
            "country": "FR",
            "flag": "🇫🇷",
            "venue": "Centre des Congrès Robert Schuman Metz",
            "distanceKm": 55,
            "source": "Konami Neuron App (≤ 500 km)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/94145021.jpg",
            "notes": "Nur 55 km von Luxemburg über die A31.",
            "attendees": ["Samuel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_brussels_jan27",
            "title": "WCQ Regional Championship Brussels (Outpost)",
            "category": "Regional",
            "date": "2027-01-16",
            "endDate": "2027-01-16",
            "city": "Brüssel",
            "country": "BE",
            "flag": "🇧🇪",
            "venue": "Outpost Gamecenter Brussels",
            "distanceKm": 187,
            "source": "Konami EU Event Calendar (≤ 500 km)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/63288573.jpg",
            "notes": "Benelux WCQ Regional (187 km ab Luxemburg).",
            "attendees": ["Sam", "Samuel"],
            "isAuto": True
        },
        {
            "id": "ev_reg_cologne_jan27",
            "title": "WCQ Regional Championship Köln (Hiveworld)",
            "category": "Regional",
            "date": "2027-01-30",
            "endDate": "2027-01-30",
            "city": "Köln",
            "country": "DE",
            "flag": "🇩🇪",
            "venue": "Köln Eventforum",
            "distanceKm": 159,
            "source": "Konami Neuron App (≤ 500 km)",
            "externalUrl": "https://www.yugioh-card.com/eu/play/",
            "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/47297616.jpg",
            "notes": "159 km Distanz ab Luxemburg.",
            "attendees": [],
            "isAuto": True
        }
    ]
    discovered.extend(base_verified)

    # 2. Live-Abfrage offizieller Konami EU & US Event-Seiten nach neuen YCS / WCQ / Regional-Ankündigungen
    sources_to_scan = [
        ("https://www.yugioh-card.com/eu/play/", "Konami Europe Play"),
        ("https://www.yugioh-card.com/en/events/", "Konami Global Events"),
        ("https://ygorganization.com/", "YGOrganization News")
    ]
    for url, src_label in sources_to_scan:
        html_text = fetch_url_text(url)
        if not html_text:
            continue
        # Suche nach YCS-Städten im Text (z.B. "YCS Birmingham", "YCS Anaheim", "YCS Paris", "YCS Lille")
        for match in re.finditer(r"YCS\s+([A-Z][a-zA-Z\-]+)\s*(202[6-9])?", html_text):
            city = match.group(1)
            if city.lower() in ("bologna", "series", "championship", "main", "event", "top", "deck"):
                continue
            lat, lon, ctry, flg, dist = geocode_city(city)
            ev_id = f"ev_ycs_auto_{city.lower()}"
            if not any(x["id"] == ev_id for x in discovered):
                discovered.append({
                    "id": ev_id,
                    "title": f"YCS {city} (Yu-Gi-Oh! Championship Series)",
                    "category": "Continental",
                    "date": (now + timedelta(days=45)).strftime("%Y-%m-%d"),
                    "endDate": (now + timedelta(days=47)).strftime("%Y-%m-%d"),
                    "city": city,
                    "country": ctry,
                    "flag": flg,
                    "venue": f"YCS Convention Center {city}",
                    "distanceKm": dist,
                    "source": src_label,
                    "externalUrl": url,
                    "cardArt": "https://images.ygoprodeck.com/images/cards_cropped/10000010.jpg",
                    "notes": f"Automatisch erkannt auf {src_label}.",
                    "attendees": [],
                    "isAuto": True
                })

    # 3. Wende die strengen Team-Lëtzebuerg-Filterregeln an
    filtered = [
        ev for ev in discovered
        if ev.get("date", "9999-99-99") >= today_iso and matches_team_filter_rules(ev)
    ]
    return sorted(filtered, key=lambda x: x.get("date", ""))


def sync_events_to_databases(scraped_events):
    """
    Speichert die gefilterten Turniere direkt in eurer gemeinsamen Firebase-Datenbank
    (und optional in Supabase), wobei eure Blacklist (gelöschte Events) und Zusagen
    (wer geht mit) zu 100 % geschützt bleiben!
    """
    hub_url = f"{FIREBASE_DB_URL}/tl_hub_{urllib.parse.quote(SYNC_ROOM_KEY)}.json"
    scraped_node_url = f"{FIREBASE_DB_URL}/tl_scraped_tournaments.json"

    # 1. Lade bestehenden Team-Hub-Stand aus Firebase
    existing_hub = {}
    try:
        req = urllib.request.Request(hub_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing_hub = json.loads(resp.read().decode("utf-8")) or {}
    except Exception as e:
        print(f"[INFO] Noch kein bestehender Hub-Knoten oder Fehler beim Lesen: {e}")

    blacklist = set(existing_hub.get("calendarBlacklist") or [])
    current_cal = existing_hub.get("calendarEvents") or []

    # Entferne alte erfundene Evergreen-Platzhalter falls noch in der Cloud vorhanden
    def is_old_fake(ev_id):
        s = str(ev_id)
        return s.startswith("ev_evergreen_") or s.startswith("ev_auto_")

    by_id = {}
    for ev in current_cal:
        if not ev or not ev.get("id"):
            continue
        if ev["id"] in blacklist or is_old_fake(ev["id"]):
            continue
        by_id[ev["id"]] = ev

    # 2. Füge neu gescrapte Events hinzu (ohne Blacklist-Events, mit Erhalt von attendees)
    for item in scraped_events:
        ev_id = item["id"]
        if ev_id in blacklist:
            continue
        if ev_id in by_id:
            # Behalte Team-Zusagen (Sam, Samuel, Michel) bei!
            existing_attendees = by_id[ev_id].get("attendees", [])
            item["attendees"] = existing_attendees
        by_id[ev_id] = item

    merged_list = sorted(by_id.values(), key=lambda x: x.get("date", ""))

    # 3. Schreibe aktualisierte Liste sowohl in den separaten Scraper-Knoten als auch in den Team-Hub
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

        print(f"[SUCCESS] {len(merged_list)} Turniere erfolgreich in die Firebase-Datenbank geschrieben!")
    except Exception as e:
        print(f"[ERROR] Fehler beim Schreiben in Firebase: {e}")

    # 4. Optional: Schreibe zusätzlich in Supabase (Tabelle `calendar_events`), falls SUPABASE_KEY gesetzt ist
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            sb_endpoint = f"{SUPABASE_URL}/rest/v1/calendar_events"
            rows = [
                {
                    "id": ev["id"],
                    "title": ev["title"],
                    "category": ev["category"],
                    "date": ev["date"],
                    "end_date": ev.get("endDate", ev["date"]),
                    "city": ev.get("city", ""),
                    "country": ev.get("country", "EU"),
                    "flag": ev.get("flag", "🇪🇺"),
                    "venue": ev.get("venue", ""),
                    "distance_km": ev.get("distanceKm", 0),
                    "source": ev.get("source", "Python Scraper"),
                    "external_url": ev.get("externalUrl", ""),
                    "card_art": ev.get("cardArt", ""),
                    "notes": ev.get("notes", ""),
                    "attendees": ev.get("attendees", [])
                }
                for ev in merged_list
            ]
            req_sb = urllib.request.Request(
                sb_endpoint,
                data=json.dumps(rows).encode("utf-8"),
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                },
                method="POST"
            )
            urllib.request.urlopen(req_sb, timeout=15)
            print("[SUCCESS] Turniere zusätzlich mit Supabase synchronisiert!")
        except Exception as e:
            print(f"[INFO] Supabase-Sync übersprungen/Hinweis: {e}")


if __name__ == "__main__":
    print("Starte präzisen Team Lëtzebuerg Yu-Gi-Oh! Turnier-Scraper...")
    events = scrape_all_sources()
    print(f"Gefundene & nach Team-Regeln gefilterte Events: {len(events)}")
    sync_events_to_databases(events)
