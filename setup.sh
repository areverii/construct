# setup.sh
#!/usr/bin/env bash
# builds the docker image and runs tests

docker build -t construct_app .
docker run --rm construct_app poetry run pytest