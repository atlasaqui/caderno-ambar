FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
RUN useradd --create-home ambar && mkdir /data && chown ambar /data
USER ambar
ENV AMBAR_DB=/data/ambar.sqlite3 AMBAR_ENV=production
EXPOSE 8000
CMD ["uvicorn", "aplicacao:criar_app", "--factory", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
