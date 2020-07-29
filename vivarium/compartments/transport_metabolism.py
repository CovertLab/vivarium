from __future__ import absolute_import, division, print_function

import os
import copy
import argparse

from vivarium.library.dict_utils import get_value_from_path
from vivarium.library.units import units
from vivarium.core.process import Generator
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_simulation_output,
    set_axes,
    COMPARTMENT_OUT_DIR)
from vivarium.parameters.parameters import (
    parameter_scan,
    get_parameters_logspace,
    plot_scan_results)

# processes
from vivarium.plots.transport_metabolism import plot_diauxic_shift
from vivarium.processes.division_volume import DivisionVolume
from vivarium.processes.meta_division import MetaDivision
from vivarium.processes.tree_mass import TreeMass
from vivarium.processes.metabolism import (
    Metabolism,
    get_iAF1260b_config)
from vivarium.processes.convenience_kinetics import (
    ConvenienceKinetics,
    get_glc_lct_config)
from vivarium.processes.ode_expression import (
    ODE_expression,
    get_lacy_config)


NAME = 'transport_metabolism'
TIMESTEP = 1

def default_metabolism_config():
    config = get_iAF1260b_config()

    # set flux bond tolerance for reactions in ode_expression's lacy_config
    metabolism_config = {
        'time_step': TIMESTEP,
        'initial_mass': 1339.0,  # fg of metabolite pools
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lcts_e': [1.05, 1.0]}}
    config.update(metabolism_config)
    return config

def default_expression_config():
    # glc lct config from ode_expression
    config = get_lacy_config()

    # redo regulation with BiGG id for glucose
    regulators = [('external', 'glc__D_e')]
    regulation = {'lacy_RNA': 'if (external, glc__D_e) > 0.1'}  # inhibited in this condition
    reg_config = {
        'regulators': regulators,
        'regulation': regulation}
    config.update(reg_config)
    return config


def default_transport_config():
    config = get_glc_lct_config()
    config['time_step'] = TIMESTEP
    return config


class TransportMetabolism(Generator):
    """
    Transport/Metabolism Compartment, with ODE expression
    """

    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('agents',),
        'daughter_path': tuple(),
        'fields_path': ('fields',),
        'dimensions_path': ('dimensions',),
        'division': {},
        'transport': default_transport_config(),
        'metabolism': default_metabolism_config(),
        'expression': default_expression_config(),
    }

    def __init__(self, config=None):
        super(TransportMetabolism, self).__init__(config)

    def generate_processes(self, config):
        daughter_path = config['daughter_path']
        agent_id = config['agent_id']

        # Transport
        transport = ConvenienceKinetics(config['transport'])

        # Metabolism
        # get target fluxes from transport, and update constrained_reaction_ids
        metabolism_config = config['metabolism']
        target_fluxes = transport.kinetic_rate_laws.reaction_ids
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # Gene expression
        expression = ODE_expression(config['expression'])

        # Mass deriver
        mass_deriver = TreeMass({})

        # Division
        # configure division condition and meta-division processes
        division_condition = DivisionVolume({})
        division_config = dict(
            config.get('division', {}),
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)
        meta_division = MetaDivision(division_config)

        return {
            'transport': transport,
            'metabolism': metabolism,
            'expression': expression,
            'mass_deriver': mass_deriver,
            'division': division_condition,
            'meta_division': meta_division,
        }

    def generate_topology(self, config):
        boundary_path = config['boundary_path']
        agents_path = config['agents_path']
        fields_path = config['fields_path']
        dimensions_path = config['dimensions_path']
        external_path = boundary_path + ('external',)
        return {
            'transport': {
                'internal': ('cytoplasm',),
                'external': external_path,
                'fields': ('null',),  # metabolism's exchange is used
                'fluxes': ('flux_bounds',),
                'global': boundary_path,
                'dimensions': dimensions_path,
            },
            'metabolism': {
                'internal': ('cytoplasm',),
                'external': external_path,
                'reactions': ('reactions',),
                'fields': fields_path,
                'flux_bounds': ('flux_bounds',),
                'global': boundary_path,
                'dimensions': dimensions_path,
            },
            'expression': {
                'counts': ('cytoplasm_counts',),
                'internal': ('cytoplasm',),
                'external': external_path,
                'global': boundary_path,
            },
            'mass_deriver': {
                'global': boundary_path,
            },
            'division': {
                'global': boundary_path,
            },
            'meta_division': {
                'global': boundary_path,
                'cells': agents_path,
            }
        }


# simulate
def test_txp_mtb_ge():
    default_test_setting = {
        'environment': {
            'volume': 1e-12 * units.L,
            'ports': {
                'fields': ('fields',),
                'external': ('boundary', 'external'),
                'dimensions': ('dimensions',),
                'global': ('boundary',),
            }},
        'timestep': 1,
        'total_time': 10}

    agent_id = '0'
    compartment = TransportMetabolism({'agent_id': agent_id})
    return simulate_compartment_in_experiment(compartment, default_test_setting)

def simulate_txp_mtb_ge(config={}, out_dir='out'):

    end_time = 2520  # 2520 sec (42 min) is the expected doubling time in minimal media
    environment_volume = 1e-14
    timeline = [
        (0, {
            ('external', 'glc__D_e'): 3.0,
            ('external', 'lcts_e'): 3.0,
        }),
        # (500, {
        #     ('external', 'glc__D_e'): 0.0,
        #     ('external', 'lcts_e'): 3.0,
        # }),
        (end_time, {})]

    sim_settings = {
        'environment': {
            'volume': environment_volume * units.L,
            'ports': {
                'fields': ('fields',),
                'external': ('boundary', 'external'),
                'dimensions': ('dimensions',),
                'global': ('boundary',),
            }},
        'timeline': {
            'timeline': timeline,
            'ports': {
                'external': ('boundary', 'external')}}
    }

    # run simulation
    agent_id = '0'
    compartment = TransportMetabolism({'agent_id': agent_id})
    timeseries = simulate_compartment_in_experiment(compartment, sim_settings)

    # calculate growth
    volume_ts = timeseries['boundary']['volume']
    print('growth: {}'.format(volume_ts[-1] / volume_ts[1]))

    ## plot
    # diauxic plot
    settings = {
        'internal_path': ('cytoplasm',),
        'external_path': ('boundary', 'external'),
        'global_path': ('boundary',),
        'environment_volume': 1e-13,  # L
        # 'timeline': timeline
    }
    plot_diauxic_shift(timeseries, settings, out_dir)

    # simulation plot
    plot_settings = {
        'max_rows': 30,
        'remove_flat': True,
        'remove_zeros': True,
        'skip_ports': ['null', 'reactions'],
    }
    plot_simulation_output(timeseries, plot_settings, out_dir)

# parameters
def scan_transport_metabolism():

    # initialize the compartment
    compartment = TransportMetabolism({})

    # parameters to be scanned, and their values
    scan_params = {
        ('transport',
         'kinetic_parameters',
         'EX_glc__D_e',
         ('internal', 'EIIglc'),
         'kcat_f'):
            get_parameters_logspace(1e3, 1e6, 3),
        ('transport',
         'kinetic_parameters',
         'EX_lcts_e',
         ('internal', 'LacY'),
         'kcat_f'):
            get_parameters_logspace(1e3, 1e6, 3),
    }

    # metrics are the outputs of a scan
    metrics = [
        ('reactions', 'EX_glc__D_e'),
        ('reactions', 'EX_lcts_e'),
        ('boundary', 'mass')
    ]

    # define conditions
    conditions = [
        {
        'environment': {
            'glc__D_e': 12.0,
            'lcts_e': 10.0},
        'cytoplasm': {
            'LacY': 0.0}
        },
        {
        'environment': {
            'glc__D_e': 0.0,
            'lcts_e': 10.0},
        'cytoplasm': {
            'LacY': 1.0e-6}
        },
    ]

    ## TODO -- add targets
    # targets = {
    #     'global', 'growth_rate'
    # }

    # set up scan options
    timeline = [(10, {})]
    sim_settings = {
        'environment': {
            'volume': 1e-14 * units.L,
            'ports': {
                'fields': ('fields',),
                'external': ('boundary', 'external'),
                'dimensions': ('dimensions',),
            }},
        'timeline': {
            'timeline': timeline,
            'ports': {
                'external': ('boundary', 'external')}}}

    # run scan
    scan_config = {
        'compartment': compartment,
        'scan_parameters': scan_params,
        'conditions': conditions,
        'metrics': metrics,
        'settings': sim_settings}
    results = parameter_scan(scan_config)

    return results


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # run scan with python vivarium/compartments/transport_metabolism.py --scan
    parser = argparse.ArgumentParser(description='transport metabolism composite')
    parser.add_argument('--scan', '-s', action='store_true', default=False, )
    parser.add_argument('--run', '-r', action='store_true', default=False, )
    args = parser.parse_args()

    if args.scan:
        results = scan_transport_metabolism()
        plot_scan_results(results, out_dir)
    else:
        config = {}
        simulate_txp_mtb_ge(config, out_dir)
