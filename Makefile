SHELL := /bin/bash

.PHONY: build local deploy

build:
sam build

local:
sam local start-api

deploy:
sam deploy --guided
