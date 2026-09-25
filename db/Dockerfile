FROM python:3.12-slim

WORKDIR /app/db

COPY db/ .
RUN pip install --no-cache-dir .

CMD ["alembic", "upgrade", "head"]
