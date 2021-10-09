import logging
import os.path

from functools import partial

import mqtt_gpio.gpio
from mqtt_gpio.mqttnode import MqttNode


class Binding(object):
    def __init__(self, mqtt, gpio):
        self._mqtt = mqtt
        self._gpio = gpio
        self._pinset_map = {}

    def _blob_id(self, blob):
        ret = []
        ret.append(str(blob['name']))
        ret.append(str(blob['status']))
        ret.append(str(blob['state']))
        ret.append(str(blob['demand']))
        return '-'.join(ret)

    def add_binding(self, blob):
        if 'pins' in blob:
            on_pinset_change = partial(self._on_pinset_change, blob)
            pinset = self._gpio.register_pinset(blob, on_pinset_change)

            if any([pin['mode'] == 'OUTPUT' for pin in blob['pins']]): 
                on_mqtt_demand = partial(self._on_mqtt_demand, blob)
            else:
                on_mqtt_demand = None

            def p(base, suffix):
                if not suffix:
                    return None
                return os.path.join(base, suffix)

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
        mqtt = self._pinset_map[self._blob_id(blob)]['mqtt']

        mqtt.state(value_name)

        status = {
            'state': value_name,
            'values': list(blob['values'].keys()),
            'topic': {
                'state': blob['state']
            },
        }
        if blob['demand']:
            status['topic']['demand'] = blob['demand']

        mqtt.status(status)

    def _on_mqtt_demand(self, blob, payload, timestamp):
        pinset = self._pinset_map[self._blob_id(blob)]['pinset']

        if blob['inch'] and timestamp < 5.0:
            logging.warning('Ignoring. Inching startup holdoff: "%s" %s', blob['name'], payload)
            return

        try:
            pinset.write(payload)
        except KeyError:
            logging.warning('Ignoring. Invalid payload: "%s" %s', blob['name'], payload)
