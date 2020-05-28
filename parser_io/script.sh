#!/usr/bin/env bash

set -eu

while getopts m:i:o:c: option
do
case "${option}"
in
c) CONFIG=${OPTARG};;
m) CMD=${OPTARG};;
i) INPUT=${OPTARG};;
o) OUTPUT=${OPTARG};;
esac
done

if ! go run "$CMD" -conf "$CONFIG" -i "$INPUT" -o "$OUTPUT"
then
    rm -f "$OUTPUT"
    echo "CFG parser failed."
    exit 1
fi
