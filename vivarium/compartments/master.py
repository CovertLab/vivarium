from __future__ import absolute_import, division, print_function

import os

from vivarium.core.experiment import Compartment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    COMPARTMENT_OUT_DIR
)
from vivarium.library.dict_utils import deep_merge
from vivarium.compartments.gene_expression import plot_gene_expression_output

# processes
from vivarium.processes.division_volume import DivisionVolume
from vivarium.processes.metabolism import Metabolism, get_iAF1260b_config
from vivarium.processes.convenience_kinetics import ConvenienceKinetics, get_glc_lct_config
from vivarium.processes.transcription import Transcription
from vivarium.processes.translation import Translation
from vivarium.processes.degradation import RnaDegradation
from vivarium.processes.complexation import Complexation


NAME = 'master'

def default_metabolism_config():
    metabolism_config = get_iAF1260b_config()
    metabolism_config.update({
        'moma': False,
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lcts_e': [1.05, 1.0]}})
    return metabolism_config



class Master(Compartment):

    defaults = {
        'global_path': ('global',),
        'external_path': ('external',),
        'config': {
            'transport': get_glc_lct_config(),
            'metabolism': default_metabolism_config()
        }
    }

    def __init__(self, config=None):
        if not config:
            config = {}
        self.config = deep_merge(self.defaults['config'], config)
        self.global_path = self.or_default(
            config, 'global_path')
        self.external_path = self.or_default(
            config, 'external_path')

    def generate_processes(self, config):

        # Transport
        transport_config = config.get('transport')
        transport = ConvenienceKinetics(transport_config)
        target_fluxes = transport.kinetic_rate_laws.reaction_ids

        # Metabolism
        # add target fluxes from transport
        metabolism_config = config.get('metabolism')
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # Expression
        transcription_config = config.get('transcription', {})
        translation_config = config.get('translation', {})
        degradation_config = config.get('degradation', {})
        transcription = Transcription(transcription_config)
        translation = Translation(translation_config)
        degradation = RnaDegradation(degradation_config)
        complexation = Complexation(config.get('complexation', {}))

        # Division
        # get initial volume from metabolism
        division_config = config.get('division', {})
        division_config.update({'initial_state': metabolism.initial_state})
        division = DivisionVolume(division_config)

        return {
            'transport': transport,
            'transcription': transcription,
            'translation': translation,
            'degradation': degradation,
            'complexation': complexation,
            'metabolism': metabolism,
            'division': division}

    def generate_topology(self, config):
        return {
            'transport': {
                'internal': ('metabolites',),
                'external': self.external_path,
                'exchange': ('null',),  # metabolism's exchange is used
                'fluxes': ('flux_bounds',),
                'global': self.global_path},

            'metabolism': {
                'internal': ('metabolites',),
                'external': self.external_path,
                'reactions': ('reactions',),
                'exchange': ('exchange',),
                'flux_bounds': ('flux_bounds',),
                'global': self.global_path},

            'transcription': {
                'chromosome': ('chromosome',),
                'molecules': ('metabolites',),
                'proteins': ('proteins',),
                'transcripts': ('transcripts',),
                'factors': ('concentrations',),
                'global': self.global_path},

            'translation': {
                'ribosomes': ('ribosomes',),
                'molecules': ('metabolites',),
                'transcripts': ('transcripts',),
                'proteins': ('proteins',),
                'concentrations': ('concentrations',),
                'global': self.global_path},

            'degradation': {
                'transcripts': ('transcripts',),
                'proteins': ('proteins',),
                'molecules': ('metabolites',),
                'global': self.global_path},

            'complexation': {
                'monomers': ('proteins',),
                'complexes': ('proteins',),
                'global': self.global_path},

            'division': {
                'global': self.global_path}}


def run_master(out_dir):
    timeseries = test_master()
    volume_ts = timeseries['global']['volume']
    print('growth: {}'.format(volume_ts[-1]/volume_ts[0]))
    expression_plot_settings = {
        'name': 'gene_expression',
        'ports': {
            'transcripts': 'transcripts',
            'molecules': 'metabolites',
            'proteins': 'proteins'}}
    plot_gene_expression_output(timeseries, expression_plot_settings, out_dir)

    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
        'skip_ports': ['prior_state', 'null', 'flux_bounds', 'chromosome', 'reactions', 'exchange']}
    plot_simulation_output(timeseries, plot_settings, out_dir)

def test_master():
    # load the compartment
    compartment_config = {
        'external_path': ('external',),
        'exchange_path': ('exchange',),
        'global_path': ('global',),
        'agents_path': ('..', '..', 'cells',)}
    compartment = Master(compartment_config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': 10}
    return simulate_compartment_in_experiment(compartment, settings)




if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_master(out_dir)
