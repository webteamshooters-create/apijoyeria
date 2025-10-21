# ---- Base: Python 3.11.9 slim ----
FROM python:3.11.9-slim

# Ajustes básicos de Python/Pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Directorio de trabajo
WORKDIR /app

# Librerías del sistema necesarias para Pillow (runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo zlib1g libpng16-16 libtiff6 libfreetype6 libopenjp2-7 libwebp7 \
 && rm -rf /var/lib/apt/lists/*

# Copiamos requirements primero para aprovechar cache
COPY requirements.txt .

# Instalar dependencias del proyecto + gunicorn
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn

# Copiar el resto del código
COPY . .

# Render proporciona la variable PORT. Exponemos un puerto por defecto para local.
EXPOSE 10000

# Ejecutar con gunicorn (ajusta "app:app" si tu módulo/objeto difiere)
# -w 2: dos workers, -k gthread: threads, -t 120: timeout generoso
CMD ["bash", "-lc", "gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:${PORT:-10000} app:app"]
