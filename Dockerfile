FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY *.py ./
COPY cogs/ ./cogs/

# Install dependencies using uv
RUN uv pip install --system --no-cache .

ENV DB_PATH=/app/data/voice.db
VOLUME /app/data

CMD ["python", "voicecreate.py"]
