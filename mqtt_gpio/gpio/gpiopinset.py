import logging

from itertools import count
from functools import partial

import gevent

from mqtt_gpio.gpio.inputpin import InputPin
from mqtt_gpio.gpio.outputpin import OutputPin

PUD = {
    'OFF': None,
    'UP': True,
    'DOWN': False,
}


class GpioPinSet:   # pylint: disable=R0902
    def __init__(self, blob, on_change):
        self._pin_factory = None
        self._pi = None
        self._blob = blob
        self._on_change = on_change
        self._pins = []
        self._values = None
        self._notify = None
        self._change_delay = blob.get('change-delay', None)
        self._inching = None
        self._inch_steps_map = None
        self._inch_queue = []
        self._inch_payload = None

        self._values_by_name = {}
        self._values_by_value = {}
        self._values_by_payload = {}
        for value_blob in self._blob['values']:
            self._values_by_name[value_blob['name']] = value_blob
            self._values_by_value[value_blob['value']] = value_blob
            if 'payload' in value_blob:
                self._values_by_payload[value_blob['payload']] = value_blob

    def _setup_pins(self):
        initial_values = self._blob.get('initial-value', None)
        if initial_values:
            initial_values = self._values_by_name[initial_values]['value']

        for pin_blob, i in zip(self._blob['pins'], count()):
            mode = pin_blob.get('mode', None)
            pull_up = PUD[pin_blob['pull-up-down']]

            if mode == 'INPUT':
                pin = InputPin(
                    pin=pin_blob['gpio'],
                    pull_up=pull_up,
                    bounce_time=pin_blob.get('bounce-time', None),
                    on_on=partial(self._on_pin_change, i, 1),
                    on_off=partial(self._on_pin_change, i, 0),
                    pin_factory=self._pin_factory,
                )
            elif mode == 'OUTPUT':
                try:
                    initial_value = bool(int(initial_values[i]))
                except (IndexError, TypeError, ValueError):
                    initial_value = None

                pin = OutputPin(
                    pin=pin_blob['gpio'],
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
        for inch_blob in self._blob.get('inch', None) or []:
            steps = []
            for step in inch_blob['steps']:
                fields = [f.strip() for f in step.strip().split(',')]
                value_name = fields[0]

                try:
                    duration = float(fields[1])
                except IndexError:
                    duration = 0

                try:
                    publish_payload = fields[2] or None
                except IndexError:
                    publish_payload = None

                if value_name not in self._values_by_name:
                    logging.error('{%s} Step "%s" not found, ignoring inch steps for %s', self._blob['name'], value_name, inch_blob['payload'])
                    steps = []
                    break
                steps.append({
                    'value-name': value_name,
                    'duration': duration,
                    'publish-payload': publish_payload
                })
            self._inch_steps_map[inch_blob['payload']] = steps

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

    def write(self, payload):
        if payload in self._inch_steps_map:
            steps = self._inch_steps_map[payload]
            self._inch_queue.extend(steps)
            self._inch_start()
        elif payload in self._values_by_payload:
            self._inch_abort(payload)
            value_name = self._values_by_payload[payload]['name']
            self._write(value_name)
        else:
            raise KeyError(payload)

    @property
    def values(self):
        return self._values

    def _inch_start(self):
        if self._inching:
            return
        self._inch_step()

    def _inch_abort(self, value_name):
        if self._inching:
            logging.warning('Aborting inching with "%s"', value_name)
            self._inching = None
            self._inch_payload = None
            self._inch_queue = []

    def _inch_step(self):
        self._inching = None
        self._inch_payload = None
        try:
            inch_blob = self._inch_queue.pop(0)
            logging.debug('Writing inch step (%s, %s)', inch_blob["value-name"], inch_blob['duration'])

            try:
                self._inch_payload = inch_blob['publish-payload']
            except KeyError:
                pass
            self._write(inch_blob['value-name'])
            self._inching = gevent.spawn_later(inch_blob['duration'], self._inch_step)

        except IndexError:
            pass
        except KeyError as ex:
            logging.warning('Inch write %s: %s', ex.__class__.__name__, ex)
            self._inch_queue = []

    def _write(self, value_name):
        value = self._values_by_name[value_name]['value']

        for pin, value, i in zip(self._pins, value, count()):
            pin.value = value
            self._values[i] = value

        logging.info('{%s} Write %s', self._blob['name'], self._values)
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
        if self._inch_payload:
            self._on_change(self._inch_payload)
            return

        try:
            payload = self._values_by_value[tuple(self._values)]['payload']
        except KeyError:
            payload = 'UNKNOWN'
            logging.warning('{%s} No payload defined for "%s"', self._blob['name'], self._values)
        self._on_change(payload)
