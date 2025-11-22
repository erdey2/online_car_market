# Backend Python image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Build arguments (to choose which requirements file to install)
ARG ENVIRONMENT=local

# Install system deps
RUN apt-get update && apt-get install -y \
    libpq-dev gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements directory
COPY requirements/ /app/requirements/

# Install Python dependencies based on environment
RUN if [ "$ENVIRONMENT" = "production" ] ; then \
        pip install --no-cache-dir -r requirements/production.txt ; \
    else \
        pip install --no-cache-dir -r requirements/local.txt ; \
    fi

# Copy project
COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
