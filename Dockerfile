# # Dockerfile
FROM python:3.12

# Installation des dépendances système
RUN apt-get update && \
    apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    python3-dev \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copie du reste du code
COPY . .

# Exposition du port
EXPOSE 8000