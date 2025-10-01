FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 libpng16-16 fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# ⬇️ code de l’app
COPY application_streamlit.py constructeur_dcop.py ./

# ⬇️ on EMBARQUE le CSV (et éventuellement d’autres fichiers) dans l’image
COPY results/ ./results/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8501
CMD ["streamlit", "run", "application_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
