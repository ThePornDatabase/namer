#!/bin/bash
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
CLEAN=$(git diff-index --quiet HEAD; echo $?)
version=$(cat pyproject.toml | grep "version = " | sed 's/.* = //' | sed 's/"//g')
if [[ "${CLEAN}" == "0" ]]; then
  export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
  export GIT_HASH=$(git rev-parse --verify HEAD)
  export repo=theporndatabase
  docker build . --build-arg "BUILD_DATE=${BUILD_DATE}" --build-arg "GIT_HASH=${GIT_HASH}" --build-arg "PROJECT_VERSION=${version}" -t "ghcr.io/${repo}/namer:${version}" -t "ghcr.io/${repo}/namer:latest"
else
  echo Not building for dirty code.
fi
