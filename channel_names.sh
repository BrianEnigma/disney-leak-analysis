#!/bin/bash

INPUT_DATA_FOLDER=/Volumes/Disney/DisneyLeak

for file in "$INPUT_DATA_FOLDER"/*.json; do
  line=$(head -n 2 "$file" | tail -n 1)
  echo "$line : $(basename "$file")"
done
