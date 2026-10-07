FROM python:3.12-slim

WORKDIR /app

COPY db/ db/
COPY admin-service/ admin-service/
RUN pip install --no-cache-dir ./db && pip install --no-cache-dir -e ./admin-service

WORKDIR /app/admin-service
EXPOSE 8002
# Forwarded headers are ignored so a client cannot claim an allowed address
CMD ["uvicorn", "admin_service.main:app", "--host", "0.0.0.0", "--port", "8002", "--no-proxy-headers", "--reload"]
