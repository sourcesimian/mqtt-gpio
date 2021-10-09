MQTT GPIO <!-- omit in toc -->
===

***MQTT to GPIO pin connector service***

A service which connects MQTT topics to GPIO pins, configurable via YAML. Additionally supports input and output pin groups, and complex inching.

# Compatability
MQTT GPIO uses the [gpiozero](https://gpiozero.readthedocs.io/) module, which builds on a number of [pin factories](https://gpiozero.readthedocs.io/en/stable/index.html?highlight=factories#pin-factories). However, I encountered a variety of technical obstacles and behaviour issues, especially since I wanted to run in a container on Kubernetes, thus at present MQTT GPIO is only tested with the `native` pin factory. Your milage may vary with the other pin factories, as was my exprience of finding my garage door standing open one morning after a server restart during the night.

Currently tested in [K3s](https://k3s.io/) (Kubernetes) running on a RasberryPi 4B.

# Containerization
Example `Dockerfile`:

```
FROM python:3.9-slim

COPY mqtt-gpio/python3-requirements.txt /
RUN pip3 install -r python3-requirements.txt

COPY mqtt-gpio/setup.py /
COPY mqtt-gpio/mqtt_gpio /mqtt_gpio
RUN python3 /setup.py develop

COPY my-config.yaml /config.yaml

ENTRYPOINT ["/usr/local/bin/mqtt-gpio", "/config.yaml"]
```

# Kubernetes
Currently tested using `native` mode run as a DaemonSet, with:
```
      volumes:
      - name: sysfs
        hostPath:
          path: /sys
```

```
      containers:
      - name: mqtt-gpio
        securityContext:
          privileged: true
        volumeMounts:
        - name: sysfs
          mountPath: /sys
          readOnly: False

```

# Development
Setup the virtualenv:

```
python3 -m venv virtualenv
. ./virtualenv/bin/activate
python3 ./setup.py develop
```

Run the server:

```
mqtt-gpio ./config-demo.yaml
```

# License

In the spirit of the Hackers of the [Tech Model Railroad Club](https://en.wikipedia.org/wiki/Tech_Model_Railroad_Club) from the [Massachusetts Institute of Technology](https://en.wikipedia.org/wiki/Massachusetts_Institute_of_Technology), who gave us all so very much to play with. The license is [MIT](LICENSE).
