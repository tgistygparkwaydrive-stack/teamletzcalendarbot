name: Weekly Yu-Gi-Oh! Tournament Scraper (Team Letzebuerg)

on:
  schedule:
    # Läuft automatisch jeden Montag um 05:00 Uhr morgens (UTC) – kostenlos für immer!
    - cron: '0 5 * * 1'
  workflow_dispatch: # Erlaubt jederzeit auch einen manuellen 1-Klick-Start auf GitHub

jobs:
  scrape-and-sync-db:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run Tournament Scraper & Push to Database
        env:
          FIREBASE_DB_URL: "https://teamletz-default-rtdb.firebaseio.com"
          SYNC_ROOM_KEY: "TeamLetzebuerg2007_OfficialSync"
          SUPABASE_URL: "https://diprvomnhjhqiypmhfhi.supabase.co"
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          python tournament_scraper.py
