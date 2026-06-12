# 🏃 Bot de Telegram para Carreras de Running en A Coruña

Bot de Telegram que te avisa automáticamente de nuevas carreras de running en Galicia, con sistema de recordatorios y seguimiento de marcas personales.

## ✨ Funcionalidades

- **Scraping diario** de carreras nuevas en webs gallegas (federaciongallegadeatletismo.gal, rockthesport.com, palmaraces.com)
- **Notificaciones automáticas** con detalles de la carrera (nombre, fecha, distancia, precio, link)
- **3 botones de respuesta**: ✅ Me apunto | ❌ Paso | 🤔 Me lo pienso
- **Recordatorios automáticos** 3 días antes de carreras aceptadas
- **Recordatorio a los 7 días** para carreras en "me lo pienso"
- **Comandos**:
  - `/miscorreras` - Lista tus carreras aceptadas
  - `/registrarmarca [nombre] [tiempo] [fecha]` - Guarda tu resultado
  - `/historial [nombre]` - Muestra tus tiempos con comparativas año a año
- **Base de datos SQLite** para persistencia de datos

## 📋 Requisitos

- Docker y Docker Compose
- Token de Telegram Bot
- Chat ID de Telegram

## 🚀 Instalación

### 1. Obtener Token de Telegram Bot

1. Abre Telegram y busca [@BotFather](https://t.me/botfather)
2. Envía `/newbot` y sigue las instrucciones
3. Copia el token que te da (algo como `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Obtener tu Chat ID

1. Busca [@userinfobot](https://t.me/userinfobot) en Telegram
2. Inicia el bot y te dará tu Chat ID (algo como `123456789`)

### 3. Configurar archivo .env

Crea el archivo `.env` en la raíz del proyecto:

```bash
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

**Ejemplo:**
```bash
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### 4. Arrancar con Docker Compose

```bash
# En la raíz del proyecto
docker-compose up -d
```

El bot se iniciará y comenzará a funcionar automáticamente.

## 📁 Estructura del Proyecto

```
telegram-running-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py           # Punto de entrada
│   ├── config.py         # Configuración (variables de entorno)
│   ├── database.py       # Modelo de datos SQLite
│   ├── scrapers.py       # Scrapers de las 3 webs
│   ├── handlers.py       # Handlers de Telegram
│   └── scheduler.py      # APScheduler para tareas automáticas
├── data/                 # Directorio para la base de datos (se crea automáticamente)
├── .env                  # Variables de entorno (crear este archivo)
├── .env.example          # Plantilla de .env
├── requirements.txt      # Dependencias Python
├── Dockerfile            # Configuración Docker
├── docker-compose.yml    # Orquestación Docker
└── README.md             # Este archivo
```

## ⏰ Programación de Tareas

El bot ejecuta las siguientes tareas automáticamente:

- **09:00** - Scraping diario de carreras nuevas
- **08:00** - Recordatorios 3 días antes de carreras aceptadas
- **Cada hora** - Verificación de recordatorios "me lo pienso"

## 📊 Comandos del Bot

### `/miscorreras`
Lista todas las carreras que has aceptado.

### `/registrarmarca [nombre] [tiempo] [fecha]`
Guarda tu marca personal en una carrera.

**Formato:**
```
/registrarmarca San Silvestre 45:30 31/12/2024
```

- `nombre`: Nombre de la carrera
- `tiempo`: Formato MM:SS o HH:MM:SS
- `fecha`: Formato DD/MM/YYYY

### `/historial [nombre]`
Muestra tu historial de tiempos en una carrera con comparativas año a año.

**Formato:**
```
/historial San Silvestre
```

Muestra:
- Todos tus tiempos ordenados por año
- Comparativa con el año anterior (📈 mejora, 📉 empeora)
- Tu mejor marca personal

## 🔧 Mantenimiento

### Ver logs del contenedor

```bash
docker-compose logs -f
```

### Detener el bot

```bash
docker-compose down
```

### Reiniciar el bot

```bash
docker-compose restart
```

### Hacer backup de la base de datos

La base de datos se guarda en `data/races.db`. Para hacer backup:

```bash
cp data/races.db data/races.db.backup
```

## 🐛 Solución de Problemas

### El bot no envía mensajes
- Verifica que el token y chat ID en `.env` son correctos
- Asegúrate de haber iniciado una conversación con el bot (@tu_bot_username)
- Revisa los logs con `docker-compose logs -f`

### No encuentra carreras
- Las webs pueden haber cambiado su estructura HTML
- Revisa los logs para ver errores de scraping
- Los scrapers pueden necesitar ajustes manuales

### Errores de base de datos
- Elimina `data/races.db` y reinicia el contenedor
- Se creará automáticamente con la estructura correcta

## 📝 Notas Importantes

- Los scrapers son genéricos y pueden necesitar ajustes según la estructura real de las webs
- Las fechas se normalizan a formato YYYY-MM-DD
- Los tiempos se guardan en formato MM:SS o HH:MM:SS
- El bot solo envía notificaciones a tu Chat ID configurado

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso personal.
