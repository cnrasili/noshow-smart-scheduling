FROM python:3.12-slim

WORKDIR /app/db

COPY constraints.txt /app/constraints.txt
COPY db/ .
RUN pip install --no-cache-dir -c /app/constraints.txt .

CMD ["alembic", "upgrade", "head"]
