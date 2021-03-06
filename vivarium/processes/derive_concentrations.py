from __future__ import absolute_import, division, print_function

from vivarium.processes.derive_globals import get_default_global_state
from vivarium.core.process import Deriver
from vivarium.library.units import units



class DeriveConcentrations(Deriver):
    """
    Process for deriving concentrations from counts
    """

    name = 'concentrations_deriver'
    defaults = {
        'concentration_keys': [],
        'initial_state': get_default_global_state(),
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        self.initial_state = self.or_default(
            initial_parameters, 'initial_state')
        self.concentration_keys = self.or_default(
            initial_parameters, 'concentration_keys')

        parameters = {}
        parameters.update(initial_parameters)

        super(DeriveConcentrations, self).__init__(parameters)

    def ports_schema(self):
        return {
            'global': {
                'volume': {
                    '_default': self.initial_state['global']['volume'].to('fL')},
                'mmol_to_counts': {
                    '_default': self.initial_state['global']['mmol_to_counts'].to('L/mmol')}},
            'counts': {
                concentration: {
                    '_divider': 'split'}
                for concentration in self.concentration_keys},
            'concentrations': {
                concentration: {
                    '_divider': 'set',
                    '_updater': 'set'}
                for concentration in self.concentration_keys}}

    def next_update(self, timestep, states):

        # states
        mmol_to_counts = states['global']['mmol_to_counts']
        counts = states['counts']

        # concentration update
        concentrations = {}
        for molecule, count in counts.items():
            concentrations[molecule] = count / mmol_to_counts

        for molecule, concentration in concentrations.items():
            assert concentration >= 0, 'derived {} concentration < 0'.format(molecule)

        return {
            'concentrations': concentrations}

# register process by invoking upon import
DeriveConcentrations()
