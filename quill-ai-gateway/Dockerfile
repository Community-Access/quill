FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered output --
# matches the convention used by GLOW's web/Dockerfile on the same host.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# No system packages beyond what pip installs are needed -- this service
# has no PDF/EPUB/OCR/audio dependencies (unlike GLOW's web image); it's
# a small HTTP API plus a server-rendered dashboard.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Runs as a non-root user -- the OpenAI key and database credentials live
# in this container's environment, so it shouldn't run as root.
RUN useradd --create-home --shell /usr/sbin/nologin gateway \
    && chown -R gateway:gateway /app
USER gateway

EXPOSE 8000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app:create_app()"]
