from bot.scrapers import scrape_all_sources

print("Iniciando scraping de prueba...\n")
races = scrape_all_sources()

print(f"\n✅ Total de carreras encontradas: {len(races)}\n")

for race in races:
    print(f"📌 {race['name']}")
    print(f"   📅 {race['date']}")
    print(f"   📏 {race.get('distance', 'N/A')}")
    print(f"   💰 {race.get('price', 'N/A')}")
    print(f"   🔗 {race['registration_link']}")
    print(f"   📍 Fuente: {race['source']}")
    print()