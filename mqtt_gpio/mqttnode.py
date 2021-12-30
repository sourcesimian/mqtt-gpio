import json
import logging


class MqttNode:
    def __init__(self, mqtt, status_path, state_path, demand_path, on_demand, qos, retain):
        self._mqtt = mqtt
        self._status_path = status_path
        self._state_path = state_path
        self._demand_path = demand_path
        self._on_demand = on_demand
        self._qos = qos
        self._retain = retain

        if demand_path:
            self._mqtt.subscribe(demand_path, self.on_payload)

    def on_payload(self, payload, timestamp):
        logging.info('Received "%s": %s', self._demand_path, payload)
        self._on_demand(payload, timestamp - self._mqtt.connect_timestamp)

    def state(self, state):
        assert isinstance(state, str)
        if not self._state_path:
            logging.warning('Skipping publish to empty topic "%s"', state)
            return
        logging.info('Publish "%s" %s', self._state_path, state)
        self._mqtt.publish(self._state_path, payload=state, qos=self._qos, retain=self._retain)

    def status(self, payload):
        if not self._status_path:
            return
        if not isinstance(payload, str):
            payload = json.dumps(payload, sort_keys=True)

        logging.debug('Publish "%s" %s', self._status_path, payload)
        self._mqtt.publish(self._status_path, payload=payload, qos=self._qos, retain=self._retain)
