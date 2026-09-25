FROM python:3.12-slim

WORKDIR /app

COPY db/ db/
COPY web/backend/ web/backend/
RUN pip install --no-cache-dir ./db && pip install --no-cache-dir -e ./web/backend

WORKDIR /app/web/backend
EXPOSE 8000
CMD ["uvicorn", "web_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
