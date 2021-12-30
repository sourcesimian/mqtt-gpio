import logging
import sys

import mqtt_gpio.select_epoll
mqtt_gpio.select_epoll.SelectEpoll.capture()  # Capture the system select.epoll(), before it is monkey patched by gevent

import gevent               # noqa: E402 pylint: disable=C0411,C0413
import gevent.monkey        # noqa: E402 pylint: disable=C0411,C0413
gevent.monkey.patch_all()
gevent.get_hub().SYSTEM_ERROR = BaseException

import mqtt_gpio.binding    # noqa: E402 pylint: disable=C0412,C0413
import mqtt_gpio.config     # noqa: E402 pylint: disable=C0412,C0413
import mqtt_gpio.gpio       # noqa: E402 pylint: disable=C0412,C0413
import mqtt_gpio.mqtt       # noqa: E402 pylint: disable=C0412,C0413
import mqtt_gpio.server     # noqa: E402 pylint: disable=C0412,C0413

FORMAT = '%(asctime)-15s %(levelname)s [%(module)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


def cli():
    config_file = 'config.yaml' if len(sys.argv) < 2 else sys.argv[1]
    config = mqtt_gpio.config.Config(config_file)

    logging.getLogger().setLevel(level=config.log_level)

    gpio = mqtt_gpio.gpio.Gpio(**config.gpio)
    mqtt = mqtt_gpio.mqtt.Mqtt(config.mqtt)
    server = mqtt_gpio.server.Server(**config.http)

    binding = mqtt_gpio.binding.Binding(mqtt, gpio)

    for item in config.bindings():
        binding.add_binding(item)

    mqtt.open()
    gpio.open()
    mqtt_loop = mqtt.run()
    server.open()

    try:
        gevent.joinall((mqtt_loop,))
    except KeyboardInterrupt:
        server.close()
        gpio.close()
        mqtt.close()
