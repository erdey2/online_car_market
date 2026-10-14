
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for WeasyPrint
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-xlib-2.0-0 \
        libgobject-2.0-0 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements/base.txt requirements/base.txt
COPY requirements/local.txt requirements/local.txt

# Install local dependencies
RUN python -m pip install \
    --retries 10 \
    --timeout 60 \
    --no-cache-dir \
    -r requirements/local.txt

# Copy project files
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
