import logging
import sys

from mqtt_gpio.select_epoll import SelectEpoll

from mqtt_gpio.gpio.gpiopinset import GpioPinSet


class Gpio:
    def __init__(self, **config):
        self._c = config
        self._pi = None
        self._pinsets = []
        self._pin_factory = None

    def register_pinset(self, blob, on_change):
        pinset = GpioPinSet(blob, on_change)
        self._pinsets.append(pinset)
        return pinset

    def open(self):
        logging.info("Open")
        self._pin_factory = self._get_pin_factory()

        for pinset in self._pinsets:
            pinset.open(self._pin_factory)

    def close(self):
        logging.info("Close")
        for pinset in self._pinsets:
            pinset.close()
        self._pinsets = []

    def _get_pin_factory(self):
        name = self._c.get('pin-factory', None)
        args = self._c.get('factory-args', None) or {}
        logging.info('Pin factory: %s %s', name, args)

        if name == 'mock':
            from gpiozero.pins.mock import MockFactory          # pylint: disable=C0415
            return MockFactory(**args)
        if name == 'rpigpio':
            from gpiozero.pins.rpigpio import RPiGPIOFactory    # pylint: disable=C0415
            return RPiGPIOFactory(**args)
        if name == 'lgpio':
            from gpiozero.pins.lgpio import LGPIOFactory        # pylint: disable=C0415
            if 'chip' in args:
                args['chip'] = 0
            return LGPIOFactory(**args)
        if name == 'rpio':
            from gpiozero.pins.rpio import RPIOFactory          # pylint: disable=C0415
            return RPIOFactory(**args)
        if name == 'pigpio':
            from gpiozero.pins.pigpio import PiGPIOFactory      # pylint: disable=C0415
            return PiGPIOFactory(**args)
        if name == 'native':
            # gpiozero native uses select.epoll, but gevent does not yet implment epoll
            import select                                       # pylint: disable=C0415
            if not getattr(select, 'epoll', None):
                select.epoll = SelectEpoll

            from gpiozero.pins.native import NativeFactory      # pylint: disable=C0415
            return NativeFactory(**args)

        logging.error('Unknown pin-factory: "%s"', name)
        sys.exit(1)
