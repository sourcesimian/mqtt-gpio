import sys
import logging

import mqtt_gpio.select_epoll  # Capture the system select.epoll(), beofre it is monkey patched by gevent

import gevent
import gevent.monkey
gevent.monkey.patch_all()
gevent.get_hub().SYSTEM_ERROR = BaseException

import mqtt_gpio.binding
import mqtt_gpio.config
import mqtt_gpio.gpio
import mqtt_gpio.mqtt
import mqtt_gpio.server

FORMAT = '%(asctime)-15s %(levelname)s [%(module)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


def cli():
    config_file = 'config-dev.yaml' if len(sys.argv) < 2 else sys.argv[1]
    config = mqtt_gpio.config.Config(config_file)

    gpio = mqtt_gpio.gpio.Gpio(**config.gpio)
    mqtt = mqtt_gpio.mqtt.Mqtt(**config.mqtt)
    server = mqtt_gpio.server.Server(**config.http)

    binding = mqtt_gpio.binding.Binding(mqtt, gpio)

    for item in config.bindings():
        binding.add_binding(item)

    mqtt.open()
    print(1)
    gpio.open()
    print(2)
    mqtt_loop = mqtt.run()
    print(3)
    server.open()
    print(4)

    try:
        gevent.joinall((mqtt_loop,))
    except KeyboardInterrupt:
        server.close()
        gpio.close()
        mqtt.close()


