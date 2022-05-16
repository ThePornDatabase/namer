#!/bin/bash

set -eo pipefail

version_bump=$1

repo="ThePornDatabase"

found=false
for bump in 'minor' 'major' 'patch'; do 
  if [[ "$version_bump" == "$bump" ]]; then
    found=true
  fi  
done

if [ $found == false ]; then
  echo invalid arguement please use on of 'minor' 'major' 'patch'
  exit 1
fi

source ./creds.sh

CLEAN=$(git diff-index --quiet HEAD; echo $?)
if [[ "${CLEAN}" != "0" ]]; then
  echo Your git repo is not clean, can\'t releases.
  exit 1
fi

if [[ -z ${PYPI_TOKEN} ]]; then
  echo PYPI_TOKEN not set, make sure you have a token for this project set in a local creds.sh file \(it\'s git ignored\)
  exit 1
fi

if [[ -z ${GITHUB_TOKEN} ]]; then
  echo GITHUB_TOKEN not set, make sure you have a token for this project set in a local creds.sh file \(it\'s git ignored\)
  exit 1
fi

if [[ -z ${GITHUB_USERNAME} ]]; then
  echo GITHUB_TOKEN not set, make sure you have a token for this project set in a local creds.sh file \(it\'s git ignored\)
  exit 1
fi

branch=$(git rev-parse --abbrev-ref HEAD)

if [[ "$branch" != "main" ]]; then
  echo May only release off of the main branch, not other branches.
fi

poetry version $version_bump
new_version=$(poetry version -s)
git add pyproject.toml

poetry run pytest
poetry run flakeheaven lint

yarn install
yarn run build

poetry build

echo build docker image before publishing pip
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_HASH=$(git rev-parse --verify HEAD)
docker build . --build-arg "BUILD_DATE=${BUILD_DATE}" --build-arg "GITHASH=${GIT_HASH}" -t "${repo}"/namer:"${new_version}"

echo publishing pip to poetry
poetry config pypi-token.pypi "${PYPI_TOKEN}"
poetry publish

echo pushing new git tag v"${new_version}"
git commit -m "prepare release v${new_version}"
git push
git tag v"${new_version}" main
git push origin v"${new_version}"

docker login ghcr.io -u ${GITHUB_USERNAME} -p ${GITHUB_TOKEN}
docker tag "${repo}"/namer:"${new_version}" ghcr.io/"${repo}"/namer:"${new_version}"
docker tag "${repo}"/namer:"${new_version}" ghcr.io/"${repo}"/namer:latest
docker push ghcr.io/"${repo}"/namer:"${new_version}"
docker push ghcr.io/"${repo}"/namer:latest
