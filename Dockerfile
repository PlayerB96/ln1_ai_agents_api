FROM python:3.10-slim-bullseye


# Variables de entorno básicas
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=es_ES.UTF-8 \
    LC_ALL=es_ES.UTF-8

WORKDIR /app

# ----------------------------
# Dependencias del sistema
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg locales \
    unixodbc unixodbc-dev odbcinst libsqliteodbc \
 && echo "es_ES.UTF-8 UTF-8" > /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

# ----------------------------
# ODBC Driver SQL Server
# ----------------------------
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
 | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] \
 https://packages.microsoft.com/debian/11/prod bullseye main" \
 > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
 && rm -rf /var/lib/apt/lists/*
# ----------------------------
# Python deps (cache friendly)
# ----------------------------
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn uvicorn

# ----------------------------
# Código
# ----------------------------
COPY . .

EXPOSE 8001

# ----------------------------
# Arranque
# ----------------------------
CMD ["gunicorn", "app:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "--timeout", "240", \
     "--bind", "0.0.0.0:8001"]
