DOCKER_BUILDKIT ?= 1
IMAGE_NAME ?= lightpath
IMAGE_VERSION ?= latest
IMAGE ?= $(IMAGE_NAME):$(IMAGE_VERSION)
RUN_ARGS ?= ./test.sh
INSPECT_ARGS ?= /bin/bash --login
PIP_CACHE ?= $(PWD)/pip_cache
EXTRA_RUN_ARGS ?= -v $(PIP_CACHE):/home/travis/.cache/pip

all: run-test

build-image: Dockerfile
	mkdir -p $(PIP_CACHE)
	DOCKER_BUILDKIT=$(DOCKER_BUILDKIT) && \
				docker build --tag $(IMAGE) --file Dockerfile --progress=plain .

run-test: build-image
	docker run -it $(EXTRA_RUN_ARGS) $(IMAGE) "$(RUN_ARGS)"

inspect: build-image
	docker run -it $(EXTRA_RUN_ARGS) $(IMAGE) "$(INSPECT_ARGS)"

.PHONY: all build-image run-test inspect
