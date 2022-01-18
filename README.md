MQTT GPIO <!-- omit in toc -->
===

***GPIO pin to MQTT bridge service***

A service which connects MQTT topics to GPIO pins, configurable via YAML. Additionally supports input and output pin groups, and complex inching.

- [Installation](#installation)
  - [Kubernetes](#kubernetes)
  - [MQTT Infrastructure](#mqtt-infrastructure)
- [Configuration](#configuration)
  - [GPIO](#gpio)
  - [MQTT](#mqtt)
    - [MQTT - Basic Auth](#mqtt---basic-auth)
    - [MQTT - mTLS Auth](#mqtt---mtls-auth)
  - [Web Server](#web-server)
  - [Logging](#logging)
  - [Bindings](#bindings)
    - [Pins](#pins)
    - [Values](#values)
    - [Inching](#inching)
- [Contribution](#contribution)
  - [Development](#development)
- [License](#license)

# Installation
Prebuilt container images are available on [Docker Hub](https://hub.docker.com/r/sourcesimian/mqtt-gpio).

## Kubernetes
Currently tested using `native` factory, run as a DaemonSet on [K3s](https://k3s.io/) on a [Raspberry Pi 4B](https://en.wikipedia.org/wiki/Raspberry_Pi) with:
```
      volumes:
      - name: config
        configMap:
          name: mqtt-gpio-config
      - name: sysfs
        hostPath:
          path: /sys
```

```
      containers:
      - name: mqtt-gpio
        image: sourcesimian/mqtt-gpio:latest
        command: ["/entrypoint.sh"]
        securityContext:
          privileged: true
        volumeMounts:
        - name: config
          mountPath: /config
        - name: sysfs
          mountPath: /sys
          readOnly: False
```
Where `entrypoint.sh` looks like [this](./docker/entrypoint.sh), and uses the `NODE_NAME` environment variable to select different config based on the host name.
```
        env:
          - name: NODE_NAME
            valueFrom:
              fieldRef:
                fieldPath: spec.nodeName
```

## MQTT Infrastructure
An installation of **mqtt-gpio** will need a MQTT broker to connect to. There are many possibilities available. [Eclipse Mosquitto](https://github.com/eclipse/mosquitto/blob/master/README.md) is a great self hosted option with many ways of installation including pre-built containers on [Docker Hub](https://hub.docker.com/_/eclipse-mosquitto).

To control the messages on your MQTT broker you may consider [mqtt-panel](https://github.com/sourcesimian/mqtt-panel/blob/main/README.md) which is a simple web app panel that gives user interactivity with MQTT topics.

# Configuration
**mqtt-gpio** consumes a single [YAML](https://yaml.org/) file. To start off you can copy [config-basic.yaml](./config-basic.yaml)


## GPIO
**mqtt-gpio** uses the [gpiozero](https://gpiozero.readthedocs.io/) module, which builds on a number of [pin factories](https://gpiozero.readthedocs.io/en/stable/index.html?highlight=factories#pin-factories). At present the only factories which have been tested are `native` and `mock`.  I encountered a variety of technical obstacles and behaviour issues in using the other factories, especially since I wanted to run in a container on Kubernetes. Expect your mileage to vary with the other pin factories, as was my exprience of finding my garage door standing open one morning after an unexpected server restart during the night. With the `native` factory there have been no such "glitches".
```
gpio:
  pin-factory: <factory>        # GPIO pin factory, currently only: mock, native
```

## MQTT
```
mqtt:
  host: <host>                  # optional: MQTT broker host, default: 127.0.0.1
  port: <port>                  # optional: MQTT broker port, default 1883
  client-id: mqtt-gpio          # MQTT client identifier, often brokers require this to be unique
  topic-prefix: <topic prefix>  # optional: Scopes the MQTT topic prefix
  auth:                         # optional: Defines the authentication used to connect to the MQTT broker
    type: <type>                # Auth type: none|basic|mtls, default: none
    ... (<type> specific options)
```

### MQTT - Basic Auth
```
    type: basic
    username: <string>          # MQTT broker username
    password: <string>          # MQTT broker password
```

### MQTT - mTLS Auth
```
    type: mtls
    cafile: <file>              # CA file used to verify the server
    certfile: <file>            # Certificate presented by this client
    keyfile: <file>             # Private key presented by this client
    keyfile_password: <string>  # optional: Password used to decrypt the `keyfile`
    protocols:
      - <string>                # optional: list of ALPN protocols to add to the SSL connection
```

## Web Server
```
http:
  bind: <bind>                  # optional: Interface on which web server will listen, default 0.0.0.0
  port: <port>                  # Port on which web server will listen, default 8080
  max-connections: <integer>    # optional: Limit the number of concurrent connections, default 100
```

## Logging
```
logging:                        # Logging settings
  level: INFO                   # optional: Logging level, default DEBUG
```

## Bindings
A binding is a functional element, which is used to connect MQTT topics and payloads to a set of GPIO pins.

Bindings are defined under the `bindings` key:
```
bindings:
- ...
```
All bindings have the following form:
```
- name: <string>              # Binding identifier
  demand: <topic>             # optional: Input MQTT topic to listen for values
  state: <topic>              # optional: Output MQTT topic to publish values
  status: <topic>             # optional: Output MQTT topic to publish full status in JSON
  qos: [0 | 1 | 2]            # optional: MQTT QoS to use, default: 1
  retain: [False | True]      # optional: Publish with MQTT retain flag, default: False
  change-delay: <duration>    # Delay notifications pin state change notifications
  initial-value: <identifier> # optional: Initial value written to pins at startup
  pins:                       # GPIO pins associated with this binding
  - (pin definitions)
  values:                     # MQTT payloads associated with this binding
  - (value definitions)
  inch:                       # optional: Inching sequences
  - (inch definitions)
```
The `change-delay` can be used to avoid glitching when inputting a multi-pin binding, thus avoiding bursts of message publications at multi bit transitions. The `<duration>` is in floating point seconds.

The `initial-value` references one of the named `values`. Only the `pins` defined as output are written.

### Pins
```
  pins:
  - gpio: <pin>               # Pin identifier, e.g.: GPIO21
    mode: <direction>         # Read/write: INPUT|OUTPUT
    pull-up-down: <pud>       # optional: Pull-up pull-down: "OFF"|UP|DOWN. Default: "OFF"
    bounce-time: <duration>   # Debounce time
```
The `bounce-time` `<duration>` is in floating point seconds.

### Values
```
  values:
  - payload: <payload>        # optional: Payload which is matched to the value
    name: <identifier>        # optional: Value identifier, referenced from inching
    value: <value>            # The pin value(s), e.g. 1 or 1,0,0,1
```
If `payload` is defined and is received on `demand`, the pin(s) will be set to `value`. Where `value` represents all the `pins` which have been defined, in the same order. Pin value is either `0` or `1`, multiple values are seperated with a `,`.

### Inching
```
  inch:
  - payload: <payload>        # Payload which is matched to this sequence
    steps:
    - <step>                  # The steps to replay when the payload is received
    - ...(repeat)
```
If `payload` is is received on `demand`, then the steps will be run. Where each `<step>` can take the following forms:
* `<identifier>, <duration>`
* `<identifier>, <duration>, <payload>`

The `<identifier>` maps to the value `<identifier>`. The `<duration>` is in floating point seconds. And the `<payload>`, if given will be published to `state`. If payload is not given and the identified `value` is associated with a `payload` then that will be published to `state` at the beginning of the step. The `<duration>` of the last step will typically be `0`.

If a value payload is received during a replay, this will abort the replay. If an inch payload is received during replay, the steps will be queued after current steps.

# Contribution
Yes sure! And please. I built **mqtt-gpio** because I couldn't find an solution to with the same capabilities. I want it to be a project that is quick and easy to get up and running, and helps open up MQTT to anyone.

Before pushing a PR please ensure that `make check` and `make test` are clean and please consider adding unit tests.

## Development
Setup the virtualenv:

```
python3 -m venv virtualenv
. ./virtualenv/bin/activate
python3 ./setup.py develop
```

Run the server:

_Note: this will only work on OS'es with [epoll](https://en.wikipedia.org/wiki/Epoll) select, this excludes MacOS._
```
mqtt-gpio ./config-demo.yaml
```

# License
In the spirit of the Hackers of the [Tech Model Railroad Club](https://en.wikipedia.org/wiki/Tech_Model_Railroad_Club) from the [Massachusetts Institute of Technology](https://en.wikipedia.org/wiki/Massachusetts_Institute_of_Technology), who gave us all so very much to play with. The license is [MIT](LICENSE).
