#!/bin/bash

TOKEN=${1}

curl --request GET --get "https://api.metadataapi.net/scenes?q=dorcelclub-2021-12-23-peeping-tom"     --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json"     --header "Accept: application/json" | jq > ./dc.json
curl --request GET --get "https://api.metadataapi.net/scenes?q=evil-angel-2022-01-03-carmela-clutch-fabulous-anal-3-way"     --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json"     --header "Accept: application/json" | jq > ./ea.json
curl --request GET --get "https://api.metadataapi.net/scenes/1678283"     --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json"     --header "Accept: application/json" | jq > ./ea.full.json
curl --request GET --get "https://api.metadataapi.net/scenes?q=brazzers-exxtra-suck-suck-blow"     --header "Authorization: Bearer ${TOKEN}" --header "Content-Type: application/json"     --header "Accept: application/json" | jq > ./ssb2.json
