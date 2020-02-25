from __future__ import absolute_import, division, print_function

import numpy as np

from vivarium.actor.process import Process


class Growth(Process):
    def __init__(self, initial_parameters={}):
        roles = {
            'global': ['mass', 'volume']}

        parameters = {'growth_rate': 0.0006}
        parameters.update(initial_parameters)
        super(Growth, self).__init__(roles, parameters)

    def default_settings(self):

        # default state
        mass = 1339  # (wet mass in fg)
        internal = {'mass': mass}
        default_state = {'global': internal}

        # default emitter keys
        default_emitter_keys = {'global': ['mass']}

        # schema
        schema = {
            'global': {
                'mass': {
                    'updater': 'set'}}}

        default_settings = {
            'state': default_state,
            'emitter_keys': default_emitter_keys,
            'schema': schema}

        return default_settings

    def next_update(self, timestep, states):
        mass = states['global']['mass']
        new_mass = mass * np.exp(self.parameters['growth_rate'] * timestep)
        return {'global': {'mass': new_mass}}
