FROM python:3.12-slim

WORKDIR /app
COPY src /app/src
ENV PYTHONPATH=/app/src
ENTRYPOINT ["python"]
