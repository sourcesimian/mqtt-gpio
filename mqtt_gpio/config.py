import hashlib
import json
import logging
import os.path
import random
import sys

import yaml

# Prevent YAML loader from interpreting 'on', 'off', 'yes', 'no' as bool
from yaml.resolver import Resolver

for ch in "OoYyNn":
    Resolver.yaml_implicit_resolvers[ch] = [x for x in
            Resolver.yaml_implicit_resolvers[ch]
            if x[0] != 'tag:yaml.org,2002:bool']

class Config(object):
    def __init__(self, config_file):
        logging.debug('Config file: %s', config_file)
        try:
            with open(config_file, 'rt') as fh:
                self._d = yaml.load(fh, Loader=yaml.Loader)
        except yaml.parser.ParserError as ex:
            logging.exception('Loading %s', config_file)
            exit(1)

        logging.debug('Config: %s', self._d)
        self._hash = hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()

        self._d['mqtt']['client-id'] += '-%s' % self._hash[8:]

    @property
    def gpio(self):
        return self._d['gpio']

    @property
    def http(self):
        return self._d['http']

    @property
    def mqtt(self):
        return self._d['mqtt']

    def bindings(self):
        def default(item, key, value):
            if key not in item:
                item[key] = value

        for item in self._d['binding']:
            if 'values' in item:
                for key in item['values'].keys():
                    item['values'][key] = self._tuple_value(item['values'][key])
            if 'initial-value' in item:
                item['initial-value'] = self._tuple_value(item['initial-value'])

            default(item, 'status', None)
            default(item, 'state', None)
            default(item, 'demand', None)
            default(item, 'inch', None)
            default(item, 'qos', 0)
            default(item, 'retain', False)
            if 'pins' in item:
                for pin in item['pins']:
                    default(pin, 'mode', 'INPUT')
                    default(pin, 'pull-up-down', 'OFF')

            yield item

    def _tuple_value(self, value):
        if isinstance(value, (int, float)):
            return (value,)
        if not value:
            return None
        return eval(value)


