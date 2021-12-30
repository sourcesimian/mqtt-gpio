import logging

from functools import partial

from mqtt_gpio.mqttnode import MqttNode
from mqtt_gpio.util import blob_hash


class Binding:
    def __init__(self, mqtt, gpio):
        self._mqtt = mqtt
        self._gpio = gpio
        self._pinset_map = {}

    def _blob_id(self, blob):
        return blob_hash(blob)

    def add_binding(self, blob):
        if 'pins' in blob:
            on_pinset_change = partial(self._on_pinset_change, blob)
            pinset = self._gpio.register_pinset(blob, on_pinset_change)

            if any((pin['mode'] == 'OUTPUT' for pin in blob['pins'])):
                on_mqtt_demand = partial(self._on_mqtt_demand, blob)
            else:
                on_mqtt_demand = None

            mqttnode = MqttNode(self._mqtt,
                                blob['status'],
                                blob['state'],
                                blob['demand'],
                                on_mqtt_demand,
                                blob['qos'],
                                blob['retain'])

            self._pinset_map[self._blob_id(blob)] = {'blob': blob, 'pinset': pinset, 'mqtt': mqttnode}
        else:
            logging.warning('Unsupported binding type "%s"', blob['type'])

    def _on_pinset_change(self, blob, value_name):
        key = self._blob_id(blob)
        mqtt = self._pinset_map[key]['mqtt']
        pinset = self._pinset_map[key]['pinset']

        mqtt.state(value_name)

        status = {
            'state': value_name,
            'payloads': [v['payload'] for v in blob.get('values', None) or [] if 'payload' in v] + [v['payload'] for v in blob.get('inch', None) or [] if 'payload' in v],
            'topic': {
                'state': blob['state']
            },
            'value': pinset.values,
        }
        if blob['demand']:
            status['topic']['demand'] = blob['demand']

        mqtt.status(status)

    def _on_mqtt_demand(self, blob, payload, timestamp):
        pinset = self._pinset_map[self._blob_id(blob)]['pinset']

        if blob['inch'] and timestamp < 5.0:
            logging.warning('{%s} Ignoring. Inching startup holdoff: %s', blob['name'], payload)
            return

        try:
            pinset.write(payload)
        except KeyError:
            logging.warning('{%s} Ignoring. Payload not recognised %s', blob['name'], payload)
