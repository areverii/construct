# use python 3.9-slim
FROM python:3.9-slim

ENV POETRY_VERSION=1.4.2
ENV PATH="/root/.local/bin:/root/.planutils/bin:${PATH}"

# install system packages, apptainer, poetry, etc.
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

WORKDIR /app

# copy configuration and package source so poetry can install
COPY pyproject.toml poetry.lock /app/
COPY construct/ /app/construct/

# install dependencies
RUN poetry install --with dev --no-interaction

# copy remaining files

# resources (TODO -- dynamic resource loading)
COPY resources/ /app/resources/

# pytests
COPY tests/ /app/tests/

# copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]