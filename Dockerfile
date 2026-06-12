# Usa una imagen base ligera
FROM python:3.11-slim

# Evitar archivos .pyc y permitir que los logs salgan en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# INSTALACIÓN ROBUSTA DE PLAYWRIGHT
# 1. Instalamos los binarios del navegador
RUN playwright install chromium
# 2. Instalamos las dependencias del sistema necesarias para esos binarios
RUN playwright install-deps chromium

# Copiar el código fuente
COPY bot/ ./bot/
# Nota: No copies el .env aquí, es mejor usar variables de entorno en el compose

CMD ["python", "-m", "bot.main"]