from __future__ import absolute_import, division, print_function

from pymongo import MongoClient
from confluent_kafka import Producer
import json

from lens.actor.actor import delivery_report

INDEX_COLUMNS = [
    'time',
    'simulation_id',
    'experiment_id']

def create_indexes(table):
    '''Create all of the necessary indexes for the given table name.'''
    for column in INDEX_COLUMNS:
        table.create_index(column)

def get_emitter(config):
    '''
    Get an emitter based on the provided config.

    config is a dict and requires three keys:
    * type: Type of emitter ('kafka' for a kafka emitter).
    * emitter: Any configuration the emitter type requires to initialize.
    * keys: A list of state keys to emit for each state label.
    '''

    emitter_type = config.get('type', 'print')

    if emitter_type == 'kafka':
        emitter = KafkaEmitter(config)
    elif emitter_type == 'database':
        emitter = DatabaseEmitter(config)
    else:
        emitter = Emitter(config)

    return {
        'object': emitter,
        'keys': config['keys']}

def get_emitter_keys(processes, topology):
    emitter_keys = {}
    for process_id, process_object in processes.iteritems():
        process_roles = topology[process_id]
        process_keys = process_object.default_emitter_keys()
        for role, keys in process_keys.iteritems():
            compartment_name = process_roles[role]
            if compartment_name in emitter_keys.keys():
                emitter_keys[compartment_name].extend(keys)
            else:
                emitter_keys[compartment_name] = keys
    # remove redudant keys
    for compartment_name, keys in emitter_keys.iteritems():
        emitter_keys[compartment_name] = list(set(keys))

    return emitter_keys

def configure_emitter(config, processes, topology):
    emitter_config = config.get('emitter', {})
    emitter_config['keys'] = get_emitter_keys(processes, topology)
    emitter_config['experiment_id'] = config.get('experiment_id')
    emitter_config['simulation_id'] = config.get('simulation_id')
    return get_emitter(emitter_config)


class Emitter(object):
    '''
    Emit data to terminal
    '''
    def __init__(self, config):
        self.config = config

    def emit(self, data):
        print(data)


class KafkaEmitter(Emitter):
    '''
    Emit data to kafka

    example:
    config = {
        'host': 'localhost:9092',
        'topic': 'EMIT'}
    '''
    def __init__(self, config):
        self.config = config
        self.producer = Producer({
            'bootstrap.servers': self.config['host']})

    def emit(self, data):
        encoded = json.dumps(data, ensure_ascii=False).encode('utf-8')

        self.producer.produce(
            self.config['topic'],
            encoded,
            callback=delivery_report)

        self.producer.flush(timeout=0.1)


class DatabaseEmitter(Emitter):
    '''
    Emit data to a mongoDB database
    '''
    def __init__(self, config):
        self.config = config
        self.simulation_id = config.get('simulation_id')
        self.experiment_id = config.get('experiment_id')

        client = MongoClient(config['url'])
        self.db = getattr(client, config.get('database', 'simulations'))
        self.table = getattr(self.db, 'output')
        create_indexes(self.table)

    def emit(self, data):
        data.update({
            'simulation_id': self.simulation_id,
            'experiment_id': self.experiment_id})

        self.table.insert_one(data)