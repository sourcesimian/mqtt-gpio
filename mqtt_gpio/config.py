import hashlib
import logging
import random
import sys

import yaml
import yaml.parser

# Prevent YAML loader from interpreting 'on', 'off', 'yes', 'no' as bool
from yaml.resolver import Resolver

for ch in "OoYyNn":
    Resolver.yaml_implicit_resolvers[ch] = [x for x in
                                            Resolver.yaml_implicit_resolvers[ch]
                                            if x[0] != 'tag:yaml.org,2002:bool']


class Config:
    def __init__(self, config_file):
        logging.info('Config file: %s', config_file)
        try:
            with open(config_file, 'rt', encoding="utf8") as fh:
                self._d = yaml.load(fh, Loader=yaml.Loader)
        except yaml.parser.ParserError:
            logging.exception('Loading %s', config_file)
            sys.exit(1)

        self._hash = hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()

        self._d['mqtt']['client-id'] += f'-{self._hash[8:]}'

    @property
    def log_level(self):
        try:
            level = self._d['logging']['level'].upper()
            return {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'WARN': logging.WARNING,
                'ERROR': logging.ERROR,
            }[level]
        except KeyError:
            return logging.DEBUG

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
        def default(blob, key, value):
            if key not in blob:
                blob[key] = value

        for blob in self._d['binding']:
            try:
                if 'values' in blob:
                    for value_blob in blob['values']:
                        if 'name' not in value_blob:
                            value_blob['name'] = value_blob['value']
                        value_blob['value'] = self._tuple_value(value_blob['value'])

                default(blob, 'status', None)
                default(blob, 'state', None)
                default(blob, 'demand', None)
                default(blob, 'inch', None)
                default(blob, 'qos', 0)
                default(blob, 'retain', False)
                if 'pins' in blob:
                    for pin in blob['pins']:
                        default(pin, 'mode', 'INPUT')
                        default(pin, 'pull-up-down', 'OFF')

                yield blob
            except (KeyError, TypeError, IndexError) as ex:
                logging.error('Ignoring binding due to %s %s: %s', ex.__class__.__name__, ex, blob)

    def _tuple_value(self, value):
        if isinstance(value, (int, float)):
            return (value,)
        if not value:
            return None
        return eval(value)  # pylint: disable=W0123
