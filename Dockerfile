FROM python:3.13-slim

RUN useradd -m appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

USER appuser
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
