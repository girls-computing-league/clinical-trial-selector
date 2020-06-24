#!/usr/bin/env bash

set -eu

CMD = $GOPATH + "/src/github.com/facebookresearch/Clinical-Trial-Parser/src/cfg/main.go"
CONFIG = $GOPATH + "/src/github.com/facebookresearch/Clinical-Trial-Parser/src/resources/config/cfg.conf"
while getopts m:i:o:c: option
do
case "${option}"
in
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
