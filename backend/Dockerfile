FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Keep the virtualenv outside /app so bind mounts do not wipe dependencies.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy rest of the code
COPY . .

# Expose port
RUN uv run playwright install --with-deps

EXPOSE 8000

# Run your app
CMD ["uv", "run", "src/app.py"]