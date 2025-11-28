SHELL := /bin/bash

.PHONY: build local deploy run

build:
	sam build

local:
	python3 main.py

deploy:
	sam deploy --guided

