# Use Python 3.9-slim as base image
FROM python:3.9-slim AS base

# Set environment variables
ENV POETRY_VERSION=1.4.2
ENV PATH="/root/.local/bin:/root/.planutils/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    default-jre \
    curl \
    ca-certificates \
    rpm2cpio \
    cpio \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh | bash -s - /root/apptainer \
    && ln -s /root/apptainer/bin/apptainer /usr/local/bin/singularity \
    && pip install --upgrade pip poetry==${POETRY_VERSION} planutils \
    && planutils install optic --yes

# Set working directory
WORKDIR /app

# Copy only dependency files first (for better caching)
COPY app/pyproject.toml app/poetry.lock /app/

# Copy `construct/` before running poetry install
COPY app/construct /app/construct

# Install dependencies
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction

# Copy the rest of the application files (using volumes for live-reloading)
COPY app/ /app/

# Copy entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]