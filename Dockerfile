# Usa una imagen base oficial de Python
FROM python:3.10-slim-bullseye

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema (ODBC y otros paquetes necesarios)
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    libodbc1 \
    odbcinst \
    libsqliteodbc \
    locales \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*


# Configurar e instalar el locale `es_ES.UTF-8`
RUN echo "es_ES.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen es_ES.UTF-8 && \
    update-locale LANG=es_ES.UTF-8

# Establecer el locale por defecto en el contenedor
ENV LANG=es_ES.UTF-8
ENV LC_ALL=es_ES.UTF-8


# Instala el controlador ODBC de SQL Server (ODBC Driver 17 for SQL Server)
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*


# Copiar los archivos del proyecto al contenedor
COPY . /app/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir gunicorn uvicorn && \
    pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 8001
EXPOSE 8001

# Comando de inicio para Gunicorn + Uvicorn
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--timeout", "240", "--bind", "0.0.0.0:8001"]
