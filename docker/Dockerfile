FROM python:3.11-slim

WORKDIR /app

# install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# copy project files
COPY . .

# install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# expose API port
EXPOSE 8000

# start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]