import requests

url = "https://atletismo.gal/competicions/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=30)

with open("html_debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"Status code: {response.status_code}")
print(f"HTML guardado en html_debug.html ({len(response.text)} caracteres)")