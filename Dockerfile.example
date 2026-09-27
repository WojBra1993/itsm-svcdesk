# Dockerfile.example - a starting point for a Python 3.13 svcdesk image.
# Copy it to "Dockerfile" (docker-compose.yml builds from ".") or replace it with your own for any language.
# Two rules from API.md section 9: install every dependency at BUILD time (the grader's sandbox has no
# network once the image is built) and listen on port 8080 inside the container.
# The checker image builds with BuildKit (it ships docker-buildx-plugin), so BuildKit-only syntax such as
# `RUN --mount=type=cache,...` or `RUN <<EOF` heredocs is fine; if check 1.03 ever says "requires BuildKit",
# you are running an old checker image: `docker pull ghcr.io/swasik/itsmlab:2026` and rerun.
FROM python:3.13-slim

WORKDIR /app

# Dependencies first, so Docker caches this layer while you edit code.
# Create requirements.txt in the repository root with pinned versions, for example (current in September 2026):
#   fastapi==0.141.1
#   uvicorn==0.52.4
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Your code lives under src/ (see src/README.md). Adjust the module path in CMD to your layout.
COPY src/ /app/src/

# The SQLite file goes to /data (a named volume in docker-compose.yml), so tickets survive a restart.
RUN mkdir -p /data
ENV SVCDESK_DB=/data/svcdesk.db

EXPOSE 8080
CMD ["uvicorn", "svcdesk.main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8080"]
