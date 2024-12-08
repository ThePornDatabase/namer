#!/bin/bash

repo=theporndatabase
version=v$(cat pyproject.toml | grep -m1 "version = " | sed 's/.* = //' | sed 's/"//g' | tr -d '[:space:]')

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
export BUILD_DATE

GIT_HASH=$(git rev-parse --verify HEAD)
export GIT_HASH

docker build . --build-arg "BUILD_DATE=${BUILD_DATE}" --build-arg "GIT_HASH=${GIT_HASH}" --build-arg "PROJECT_VERSION=${version}" -t "ghcr.io/${repo}/namer:${version}" -t "ghcr.io/${repo}/namer:latest"
