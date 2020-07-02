#!/usr/bin/env bash

set -eu

CMD="${GOPATH}/src/github.com/facebookresearch/Clinical-Trial-Parser/src/cmd/cfg/main.go"
CONFIG="${GOPATH}/src/github.com/facebookresearch/Clinical-Trial-Parser/src/resources/config/cfg.conf"
echo $CMD
echo $CONFIG

while getopts m:i:o:c: option
do
case "${option}"
in
i) INPUT=${OPTARG};;
o) OUTPUT=${OPTARG};;
esac
done
echo go run $CMD -conf $CONFIG -i "$INPUT" -o "$OUTPUT"
if ! /usr/local/go/bin/go run $CMD -conf $CONFIG -i "$INPUT" -o "$OUTPUT"
then
    rm -f "$OUTPUT"
    echo "CFG parser failed."
    exit 1
fi
