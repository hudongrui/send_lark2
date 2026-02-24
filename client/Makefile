APP = send_lark_webhook
VERSION = v1.1.3
PORT = 5000
LOG_PATH = /tmp/${APP}/log

# Helper functions to avoid annoying one-line scripts invokes from makefile
CONTAINER_ID = $(shell echo `docker ps | grep ${APP} | sed 's/ .*//'`)
GET_CONTAINER = $(eval CONTAINER=$(CONTAINER_ID))

# Make targets
.PHONY: test run stop run_local build debug install freeze all release
install:
	@echo "Installing required Python packages locally."
	uv pip install --no-cache-dir -r requirements.txt --index-url https://bytedpypi.byted.org/simple/
	source .venv/bin/activate

	@echo "Updating config files..."
	@sed "s|__LOG_PATH__|${LOG_PATH}|g" conf/example.config.ini > conf/config.ini
	@sed "s|__LOG_PATH__|${LOG_PATH}|g" conf/example.logging_config.json > conf/logging_config.json
	@sed -i '' "s|__CLIENT_PORT__|${PORT}|g" conf/config.ini
	@echo "Done."

build:
	@echo "Building docker image for ${APP}:${VERSION}..."
	@echo ${VERSION} > version.latest
	docker build --no-cache --platform linux/amd64 -f Dockerfile -t ${APP}:${VERSION} .

release:
	@mkdir -p release
	docker save ${APP}:${VERSION} > release/${APP}_${VERSION}.tar
	@echo "[`date`] Saved docker image under 'release/${APP}_${VERSION}.tar'"

run_local:
	@echo "Run app on local machine."
	@mkdir -p /tmp/${APP}/log
	python3 -m uvicorn main:app --reload --log-config conf/logging_config.json

run:
	@echo "Run local container."
	@mkdir -p /tmp/${APP}/log
	@docker-compose up -d
	@sleep 1
	@docker ps

stop:
	@echo "Remove running containers for docker image '${APP}:${VERSION}'"
	@$(GET_CONTAINER)
	docker kill $(CONTAINER)

debug:
	@$(GET_CONTAINER)
	@docker exec -it $(CONTAINER) /bin/bash

test:
	@echo "[`date`]Run PyTest framework"
	@uv run pytest --capture=no -v test

all: test build release
