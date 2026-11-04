#!/usr/bin/env sh
# Start the server first:  listing-writer-ae serve --provider mock
set -e
BASE=${BASE:-http://127.0.0.1:8000}

# 1) generate a listing from a bundled SAMPLE property
curl -s "$BASE/api/samples/02-jvc-studio-rent.json" > /tmp/prop.json
curl -s -X POST "$BASE/api/generate" -H 'Content-Type: application/json' \
  --data "{\"property\": $(cat /tmp/prop.json)}" | python -m json.tool | head -40

# 2) check an existing ad without property data
curl -s -X POST "$BASE/api/check" -H 'Content-Type: application/json' \
  --data '{"text": "Best price in JVC! Guaranteed 10% ROI. عائد مضمون"}' | python -m json.tool
