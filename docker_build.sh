#!/bin/bash
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
CLEAN=$(git diff-index --quiet HEAD; echo $?)
#if [[ "${CLEAN}" == "0" ]]; then
  GIT_HASH=$(git rev-parse --verify HEAD)
  docker build . --build-arg "BUILD_DATE=${BUILD_DATE}" --build-arg "GIT_HASH=${GIT_HASH}" -t porndb/namer
#else
#  echo Not building for dirty code.
#fi
