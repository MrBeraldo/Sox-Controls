# ============================
# SOX Controls Dashboard – Gold Edition
# Dockerfile
# ============================

# Etapa 1: imagem base leve com Python
FROM python:3.11-slim

# Evita prompts interativos e melhora logs
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos para dentro da imagem
COPY . /app

# Instala dependências do sistema (para openpyxl, pandas, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Define porta padrão do Streamlit
EXPOSE 8501

# Configurações do Streamlit (sem prompts)
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ENABLECORS=false \
    STREAMLIT_SERVER_ENABLEXsrfProtection=false

# Comando para iniciar o app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
