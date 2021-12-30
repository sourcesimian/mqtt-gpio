#!/bin/sh

CONFIG=/config/config-$NODE_NAME.yaml

if [ ! -e "$CONFIG" ]; then
    echo "! Config file not found: $CONFIG" >&2
    sleep infinity
fi

exec /usr/local/bin/mqtt-gpio "$CONFIG"
