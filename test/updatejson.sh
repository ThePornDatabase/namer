#!/bin/bash

TOKEN=${1}

curl --request GET --get "https://api.metadataapi.net/scenes?q=dorcelclub-2021-12-23-peeping-tom" --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json" --header "Accept: application/json" > ./dc.json
curl --request GET --get "https://api.metadataapi.net/scenes?q=evil-angel-2022-01-03-carmela-clutch-fabulous-anal-3-way" --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json" --header "Accept: application/json" > ./ea.json
curl --request GET --get "https://api.metadataapi.net/scenes/1678283" --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json" --header "Accept: application/json" > ./ea.full.json
curl --request GET --get "https://api.metadataapi.net/scenes?q=brazzers-exxtra-suck-suck-blow" --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json" --header "Accept: application/json" > ./ssb2.json
curl --request GET --get "https://api.metadataapi.net/movies?q=petite18.Harper%20Red&limit=25" --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json" --header "Accept: application/json" > ./p18.json
