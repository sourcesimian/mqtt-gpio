import logging
import operator
import os.path
import time

import gevent

from itertools import count
from functools import partial

from mqtt_gpio.select_epoll import SelectEpoll

from gpiozero import Button, LED

PUD = {
    'OFF': None,
    'UP': True,
    'DOWN': False,
}


class Gpio(object):
    def __init__(self, **config):
        self._c = config
        self._pi = None
        self._pinsets = []

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
        logging.debug('Pin factory: %s %s', name, args)

        if name == 'mock':
            from gpiozero.pins.mock import MockFactory
            return MockFactory(**args)
        elif name == 'rpigpio':
            from gpiozero.pins.rpigpio import RPiGPIOFactory
            return RPiGPIOFactory(**args)
        elif name == 'lgpio':
            from gpiozero.pins.lgpio import LGPIOFactory
            if 'chip' in args:
                args['chip'] = 0
            return LGPIOFactory(**args)
        elif name == 'rpio':
            from gpiozero.pins.rpio import RPIOFactory
            return RPiGPIOFactory(**args)
        elif name == 'pigpio':
            from gpiozero.pins.pigpio import PiGPIOFactory
            return PiGPIOFactory(**args)
        elif name == 'native':
            # gpiozero native uses select.epoll, but gevent does not yet implment epoll
            import select
            if not getattr(select, 'epoll', None):
                select.epoll = SelectEpoll

            from gpiozero.pins.native import NativeFactory
            return NativeFactory(**args)
        else:
            logging.error('Unknown pin-factory: "%s"', name)
            exit(1)


class GpioPinSet(object):
    def __init__(self, blob, on_change):
        self._pi = None
        self._c = blob
        self._on_change = on_change
        self._pins = []
        self._values = None
        self._notify = None
        self._change_delay = blob.get('change-delay', None)
        self._inching = None
        self._inch_queue = []
        self._inch_name = None

        self._name_value_map = {}
        self._value_name_map = {}
        for name, value in self._c['values'].items():
            self._name_value_map[name] = value
            self._value_name_map[value] = name

    def _setup_pins(self):
        initial_values = self._c.get('initial-value', None)

        for blob, i in zip(self._c['pins'], count()):
            mode = blob.get('mode', None)
            pull_up = PUD[blob.get('pull-up-down', 'OFF')]

            if mode == 'INPUT':
                pin = InputPin(
                    pin=blob['gpio'],
                    pull_up=pull_up,
                    bounce_time=blob.get('bounce-time', None),
                    on_on=partial(self._on_pin_change, i, 1),
                    on_off=partial(self._on_pin_change, i, 0),
                    pin_factory=self._pin_factory,
                )
            elif mode == 'OUTPUT':
                try:
                    initial_value = True if int(initial_values[i]) else False
                except (IndexError, TypeError, ValueError):
                    initial_value = None

                pin = OutputPin(
                    pin=blob['gpio'],
                    pull_up=pull_up,
                    initial_value=initial_value,
                    pin_factory=self._pin_factory,
                )
            else:
                logging.warning('Ignoring pin with unknown mode: "%s"', mode)
                continue
            self._pins.append(pin)

    def _setup_inch_map(self):
        self._inch_steps_map = {}
        inch = self._c.get('inch', None) or {}
        for key, blob in inch.items():
            steps = []
            for step in blob:
                fields = [f.strip() for f in step.strip().split(',')]
                value_name = fields[0]

                try:
                    duration = float(fields[1])
                except IndexError:
                    duration = 0

                try:
                    inch_name = fields[2] or None
                except IndexError:
                    inch_name = None

                if value_name not in self._name_value_map:
                    logging.error('Step "%s" not found for "%s", ignoring sequence', value_name, self._name)
                    steps = []
                    break
                steps.append({
                    'value-name': value_name,
                    'duration': duration,
                    'inch-name': inch_name
                })
            self._inch_steps_map[key] = steps

    def open(self, pin_factory):
        self._pin_factory = pin_factory
        self._setup_pins()
        self._setup_inch_map()

        self._values = []
        for pin in self._pins:
            self._values.append(pin.value)
        self._notify_value_change()

    def close(self):
        for pin in self._pins:
            pin.close()

        self._in_write = 0

    def write(self, value_name):
        if self._inch_steps_map and value_name in self._inch_steps_map:
            steps = self._inch_steps_map[value_name]
            self._inch_queue.extend(steps)
            self._inch_start()
        elif value_name in self._name_value_map:
            self._inch_abort(value_name)
            self._write(value_name)
        else:
            raise KeyError(value_name)

    def _inch_start(self):
        if self._inching:
            return
        self._inch_step()

    def _inch_abort(self, value_name):
        if self._inching:
            logging.warning('Aborting inching with "%s"', value_name)
            self._inching = None
            self._inch_name = None
            self._inch_queue = []

    def _inch_step(self):
        self._inching = None
        self._inch_name = None
        try:
            blob = self._inch_queue.pop(0)
            logging.debug('Writing inch step (%s, %s)', blob["value-name"], blob['duration'])

            try:
                self._inch_name = blob["inch-name"]
            except KeyError:
                pass
            self._write(blob["value-name"])
            self._inching = gevent.spawn_later(blob['duration'], self._inch_step)

        except IndexError:
            pass
        except KeyError as ex:
            logging.warning('Inch write %s: %s', ex.__class__.__name__, ex)
            self._inch_queue = []

    def _write(self, value_name):
        value = self._name_value_map[value_name]

        for pin, value, i in zip(self._pins, value, count()):
            pin.value = value
            self._values[i] = value
        
        logging.debug('Write "%s" %s', self._c['name'], self._values)
        self._notify_value_change()

    def _on_pin_change(self, index, value):
        self._values[index] = value

        if self._change_delay:
            if self._notify and not self._notify.dead:
                return
            
            self._notify = gevent.spawn_later(self._change_delay, self._notify_value_change)
        else:
            self._notify_value_change()

    def _notify_value_change(self):
        if self._inch_name:
            self._on_change(self._inch_name)
            return

        try:
            value_name = self._value_name_map[tuple(self._values)]
        except KeyError:
            value_name = '%s' % self._values 
        self._on_change(value_name)


class InputPin(object):
    def __init__(self, pin, pull_up, bounce_time, pin_factory, on_on, on_off):
        if pull_up is None:
            active_state = True
            self._invert_value = False
        elif pull_up is True:
            active_state = None
            self._invert_value = True
        elif pull_up is False:
            active_state = None
            self._invert_value = False

        self._button = Button(
            pin=pin,
            pull_up=pull_up,
            active_state=active_state,
            bounce_time=bounce_time,
            pin_factory=pin_factory,
        )

        self._button.when_pressed = on_off if self._invert_value else on_on
        self._button.when_released = on_on if self._invert_value else on_off

    def close(self):
        self._button.when_pressed = None
        self._button.when_released = None
        self._button.close()

    @property
    def value(self):
        if self._invert_value:
            return 1 if self._button.value == 0 else 0
        return self._button.value


class OutputPin(object):
    def __init__(self, pin, pull_up, initial_value, pin_factory):
        if pull_up is None:
            active_high = True
            self._invert_value = False
        elif pull_up is True:
            active_high = True
            self._invert_value = False
        elif pull_up is False:
            active_high = False
            self._invert_value = True

        if initial_value is not None and active_high is False:
            initial_value = not initial_value

        print('OUT', pin, active_high, initial_value)
        self._led = LED(
            pin=pin,
            active_high=active_high,
            initial_value=initial_value,
            pin_factory=pin_factory,
        )

    @property
    def value(self):
        if self._invert_value is True:
            return 1 if self._led.value == 0 else 0
        return self._led.value

    @value.setter
    def value(self, value):
        if self._invert_value:
            self._led.value = 1 if value == 0 else 0
        else:
            self._led.value = value

    def close(self):
        self._led.close()
