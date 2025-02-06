# use python 3.9-slim as base image
FROM python:3.9-slim

# set env variables
ENV POETRY_VERSION=1.4.2
ENV PATH="/root/.local/bin:/root/.planutils/bin:${PATH}"

# install system dependencies, apptainer, poetry, and planutils
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
    && pip install --upgrade pip \
    && pip install poetry==${POETRY_VERSION} planutils \
    && planutils install optic --yes

# set working directory
WORKDIR /app

# copy dependency files from app (not from app/construct)
COPY app/pyproject.toml app/poetry.lock /app/

# copy the construct folder (with your .py files)
COPY app/construct /app/construct

# install dependencies
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction

# copy the rest of app (overwriting if needed)
COPY app/ /app/

# copy entrypoint script and make executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]