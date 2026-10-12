FROM python:3.12-slim

WORKDIR /app

COPY constraints.txt .
COPY db/ db/
COPY overbooking-service/ overbooking-service/
RUN pip install --no-cache-dir -c constraints.txt ./db \
    && pip install --no-cache-dir -c constraints.txt -e ./overbooking-service

WORKDIR /app/overbooking-service
EXPOSE 8001
CMD ["uvicorn", "overbooking_service.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
