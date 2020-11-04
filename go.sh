#!/usr/bin/env bash
set -eu

PLANT_UML_JAR="$HOME/lib/master/plantuml.jar"

OUTPUT_FILE_NAME=sql_dependencies
temp_file=$(mktemp "${OUTPUT_FILE_NAME}.XXXXXX")
python dependencies.py "$@" > ${temp_file}
java -jar ${PLANT_UML_JAR} -teps ${temp_file}

echo "グラフを出力しました: ${OUTPUT_FILE_NAME}.eps"

