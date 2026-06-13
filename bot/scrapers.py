import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import asyncio
import re
from datetime import datetime

def scrape_atletismo_gal() -> List[Dict]:
    """Scrapea el calendario de carreras de atletismo.gal, filtrando solo
    las de la delegación de A Coruña (provincia)."""
    
    races = []
    url = "https://atletismo.gal/competicions/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30000)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return races

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article', class_='competition')

    for article in articles:
        classes = article.get('class', [])

        # Solo carreras de la delegación de A Coruña
        if 'delegation-a-coruna' not in classes:
            continue

        # Fecha (formato DD/MM/YYYY)
        date_div = article.find('div', class_=lambda c: c and 'bg-red' in c)
        date_str = None
        if date_div:
            span = date_div.find('span')
            if span:
                date_str = span.get_text(strip=True)

        date = None
        if date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                date = f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Nombre y enlace
        h2 = article.find('h2')
        name = None
        link = None
        if h2:
            a = h2.find('a')
            if a:
                name = a.get_text(strip=True)
                link = a.get('href')

        if not name or not date:
            continue

        # Ubicación (concello)
        location = None
        loc_div = article.find('div', class_=lambda c: c and 'basis-3/12' in c)
        if not loc_div:
            loc_div = article.find('div', class_=lambda c: c and 'basis-5/12' in c)
        if loc_div:
            location = loc_div.get_text(strip=True)

        race = {
            'name': name,
            'date': date,
            'distance': 'N/A',
            'price': 'N/A',
            'registration_link': link,
            'source': 'atletismo_gal',
            'location': location or 'N/A'
        }

        races.append(race)

    return races

MESES_GL = {
    'xaneiro': '01', 'xan': '01',
    'febreiro': '02', 'feb': '02',
    'marzo': '03', 'mar': '03',
    'abril': '04', 'abr': '04',
    'maio': '05', 'mai': '05',
    'xuño': '06', 'xuñ': '06',
    'xullo': '07', 'xul': '07',
    'agosto': '08', 'ago': '08',
    'setembro': '09', 'set': '09',
    'outubro': '10', 'out': '10',
    'novembro': '11', 'nov': '11',
    'decembro': '12', 'dec': '12',
}

PALABRAS_CORUNA = [
    "a coruña", "coruña", "laracha", "oleiros", "arteixo", "culleredo",
    "cambre", "sada", "betanzos", "carballo", "ferrol", "neda", "narón",
    "ares", "ponteceso", "carral", "bergondo", "abegondo", "paderne",
    "pontedeume", "cabanas", "miño", "mugardos", "fene", "valdoviño",
    "cedeira", "ortigueira", "as pontes", "san sadurniño", "moeche",
    "irixoa", "curtis", "sobrado", "monfero", "vilarmaior", "cerdido",
    "somozas", "xermade", "malpica", "laxe", "muxía", "dumbría", "cee",
    "corcubión", "fisterra", "carnota", "a baña", "trazo", "brión",
    "ames", "negreira", "lousame", "cabana de bergantiños", "coristanco",
    "mesoiro", "ventorrillo", "volta a oza", "melide"
]

def _normalize_date_gl(fecha_str: str):
    """Convierte 'DD de mes[.] de YYYY' (gallego) a YYYY-MM-DD."""
    match = re.search(r'(\d{1,2})\s+de\s+(\w+)\.?\s+de\s+(\d{4})', fecha_str.lower())
    if not match:
        return None
    day, month_name, year = match.groups()
    month_name = month_name.rstrip('.')
    month = MESES_GL.get(month_name)
    if not month:
        return None
    return f"{year}-{month}-{day.zfill(2)}"

async def _scrape_carreirasgalegas_async():
    from playwright.async_api import async_playwright

    eventos = []
    vistos = set()
    url = "https://www.carreirasgalegas.com/events"

    print("DEBUG [CarreirasGalegas]: Iniciando Playwright...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                locale="gl-ES",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            print("DEBUG [CarreirasGalegas]: Navegando a la URL...")
            # 'domcontentloaded' evita que se quede colgado esperando analytics/trackers pesados
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            
            print("DEBUG [CarreirasGalegas]: Esperando contenedor de carreras...")
            try:
                await page.wait_for_selector(".results-month", timeout=10000)
            except Exception:
                print("DEBUG [CarreirasGalegas]: Aviso: .results-month no apareció, intentando continuar...")

            print("DEBUG [CarreirasGalegas]: Desplazando scroll...")
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(400)

            html = await page.content()
            await browser.close()
            print("DEBUG [CarreirasGalegas]: Navegador cerrado correctamente.")
    except Exception as e:
        print(f"ERROR CRÍTICO en _scrape_carreirasgalegas_async: {e}")
        return []

    print("DEBUG [CarreirasGalegas]: Parseando HTML con BeautifulSoup...")
    soup = BeautifulSoup(html, "html.parser")

    for tr in soup.select(".results-month tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        enlace = tds[1].find("a", href=re.compile(r"^/events/"))
        if not enlace:
            continue

        href = enlace.get("href", "")
        url_e = f"https://www.carreirasgalegas.com{href}"
        if url_e in vistos:
            continue
        vistos.add(url_e)

        eventos.append({
            'name': enlace.get_text(strip=True),
            'fecha_raw': tds[0].get_text(strip=True),
            'location': tds[2].get_text(strip=True),
            'url': url_e,
        })

    return eventos

async def scrape_carreirasgalegas():
    """Scrapea carreirasgalegas.com, filtrando A Coruña y el mes actual."""
    races = []

    try:
        # Ejecutamos la función asíncrona de extracción de datos reales
        eventos = await _scrape_carreirasgalegas_async()
    except ImportError:
        print("  Playwright no instalado, omitiendo carreirasgalegas")
        return races
    except Exception as e:
        print(f"  Error: {e}")
        return races

    # Obtenemos el año y mes actual para el filtro (Ej: '2026-06')
    mes_actual = datetime.now().strftime('%Y-%m')

    for e in eventos:
        date = _normalize_date_gl(e['fecha_raw'])
        if not date or not date.startswith(mes_actual):
            continue

        if not any(p in e['location'].lower() for p in PALABRAS_CORUNA):
            continue

        races.append({
            'name': e['name'],
            'date': date,
            'distance': 'N/A',
            'price': 'N/A',
            'registration_link': e['url'],
            'source': 'carreirasgalegas',
            'location': e['location'],
        })

    return races

async def scrape_all_sources() -> List[Dict]:
    """Ejecuta todos los scrapers y devuelve una lista unificada de carreras."""
    all_races = []

    print("Scraping atletismo_gal...")
    try:
        races_atletismo = scrape_atletismo_gal()
        all_races.extend(races_atletismo)
        print(f"  Found {len(races_atletismo)} races")
    except Exception as e:
        print(f"  Error: {e}")

    print("Scraping carreirasgalegas...")
    try:
        races_carreiras = await scrape_carreirasgalegas()
        all_races.extend(races_carreiras)
        print(f"  Found {len(races_carreiras)} races")
    except Exception as e:
        print(f"  Error: {e}")

    return all_races
