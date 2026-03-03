# Makefile for building App to Docker application
# @Author dongruihu
# @Date: 2025/06/18
#
#  - install:	Install required Python packages, from 'requirements.txt'
#  - build:	Build docker image application w/ current version. To overwrite version info, try: $ make VERSION=$VERSION build
#  - release:	Save docker image to 'release/*.tar'
#  - run_local:	Run program locally with 'python3 -m flask run', for development testing.
#  - run:	Run docker container under local Docker environment, for testing.
#  - stop:	Stop docker container from local Docker environment.
#  - test:	Run unittest. To specify a particular module for test, follow Python unittest syntax and specify module name.


# Specify variables here.
APP = lark_msg_service
VERSION = v1.0.9
PORT = 5000
LOG_PATH = /tmp/${APP}/log

# FIXME: change here.
LARK_APP_ID = 
LARK_APP_SECRET = 
LARK_CARD_TEMPLATE_ID = 


# Helper functions to avoid annoying one-line scripts invokes from makefile
CONTAINER_ID = $(shell echo `docker ps | grep ${APP} | sed 's/ .*//'`)
GET_CONTAINER = $(eval CONTAINER=$(CONTAINER_ID))

# Make targets
.PHONY: build release run_local run stop install all test debug freeze
install:
	@echo "Installing required Python packages locally."
	uv pip install --no-cache-dir -r requirements.txt --index-url https://bytedpypi.byted.org/simple/
	source .venv/bin/activate

	@echo "Updating config files..."
	@sed "s|__LOG_PATH__|${LOG_PATH}|g" conf/example.config.ini > conf/config.ini
	@sed "s|__LOG_PATH__|${LOG_PATH}|g" conf/example.logging_config.json > conf/logging_config.json
	@sed -i '' "s|__PORT__|${PORT}|g" conf/config.ini
	@sed -i '' "s|__APP_ID__|${LARK_APP_ID}|g" conf/config.ini
	@sed -i '' "s|__APP_SECRET__|${LARK_APP_SECRET}|g" conf/config.ini
	@echo "Done."

build:
	@echo "Building docker image for ${APP}:${VERSION}..."
	@echo ${VERSION} > version.latest
	docker build --no-cache --platform linux/amd64 -f Dockerfile -t ${APP}:${VERSION} .

release:
	@mkdir -p release
	docker save ${APP}:${VERSION} > release/${APP}_${VERSION}.tar
	@echo "[`date`] Saved docker image under 'release/${APP}_${VERSION}.tar'"

debug:
	@$(GET_CONTAINER)
	@echo "Entering container ${CONTAINER}"
	docker exec -it ${CONTAINER} /bin/bash

run_local:
	@echo "Run app on local machine."
	@mkdir -p /tmp/${APP}/log
	@echo ${VERSION} > version.latest
	python3 -m uvicorn main:app --reload --log-config conf/logging_config.json --port ${PORT} --host=0.0.0.0

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

test:
	@echo "[`date`] Running PyTest Framework under test directory..."
	@export PYTHONPATH='.'; uv run pytest --capture=no -v test

all: test build release
