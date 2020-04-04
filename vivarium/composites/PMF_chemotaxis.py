from __future__ import absolute_import, division, print_function

import os

from vivarium.compartment.process import (
    initialize_state
)
from vivarium.compartment.composition import (
    get_derivers,
    simulate_with_environment,
    plot_simulation_output,
    load_compartment)

# processes
from vivarium.processes.ode_expression import ODE_expression, get_flagella_expression
from vivarium.processes.Endres2006_chemoreceptor import ReceptorCluster
from vivarium.processes.Mears2014_flagella_activity import FlagellaActivity
from vivarium.processes.membrane_potential import MembranePotential
from vivarium.processes.convenience_kinetics import ConvenienceKinetics, get_glc_lct_config
from vivarium.processes.metabolism import Metabolism, get_e_coli_core_config
from vivarium.processes.division import Division, divide_condition


def compose_pmf_chemotaxis(config):
    receptor_parameters = {'ligand': 'GLC'}
    receptor_parameters.update(config)

    # declare the processes
    # TODO -- override transport config's glucose name
    transport_config = get_glc_lct_config()

    transport = ConvenienceKinetics(config.get('transport', transport_config))
    metabolism = Metabolism(config.get('metabolism', get_e_coli_core_config()))
    expression = ODE_expression(config.get('expression', get_flagella_expression()))
    receptor = ReceptorCluster(config.get('receptor', receptor_parameters))
    flagella = FlagellaActivity(config.get('flagella', {}))
    PMF = MembranePotential(config.get('PMF', {}))
    division = Division(config.get('division', {}))

    # place processes in layers
    processes = [
        {'PMF': PMF},
        {'receptor': receptor,
         'transport': transport
         },
        {
         # 'metabolism': metabolism,
         'expression': expression},
        {'flagella': flagella},
        {'division': division}]

    # make the topology.
    # for each process, map process ports to store ids
    topology = {
        'receptor': {
            'external': 'environment',
            'internal': 'cytoplasm'},
        'transport': {
            'exchange': 'exchange',
            'external': 'environment',
            'internal': 'cytoplasm',
            'fluxes': 'fluxes',
            'global': 'global'},
        # 'metabolism': {
        #     'internal': 'cytoplasm',
        #     'external': 'environment',
        #     'reactions': 'reactions',
        #     'exchange': 'exchange',
        #     'flux_bounds': 'fluxes'},
        'expression' : {
            'counts': 'cell_counts',
            'internal': 'cytoplasm',
            'external': 'environment'},
        'flagella': {
            'flagella_counts': 'cell_counts',
            'internal': 'cytoplasm',
            'membrane': 'membrane',
            'flagella_activity': 'flagella',
            'external': 'environment'},
        'PMF': {
            'external': 'environment',
            'membrane': 'membrane',
            'internal': 'cytoplasm'},
        'division': {
            'global': 'global'}}

    # add derivers
    derivers = get_derivers(processes, topology)
    processes.extend(derivers['deriver_processes'])  # add deriver processes
    topology.update(derivers['deriver_topology'])  # add deriver topology

    # initialize the states
    states = initialize_state(processes, topology, config.get('initial_state', {}))

    options = {
        'name': 'PMF_chemotaxis_composite',
        'topology': topology,
        'initial_time': config.get('initial_time', 0.0),
        'environment_port': 'environment',
        'exchange_port': 'exchange',
        'divide_condition': divide_condition}

    return {
        'processes': processes,
        'states': states,
        'options': options}



if __name__ == '__main__':

    out_dir = os.path.join('out', 'tests', 'PMF_chemotaxis')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    boot_config = {}  #'emitter': 'null'}
    compartment = load_compartment(compose_pmf_chemotaxis, boot_config)

    # settings for simulation and plot
    options = compartment.configuration
    timeline = [(10, {})]

    settings = {
        'environment_port': options['environment_port'],
        'exchange_port': options['exchange_port'],
        'environment_volume': 1e-13,
        'timeline': timeline,
    }

    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
        'overlay': {
            'reactions': 'flux_bounds'},
        'skip_ports': [
            'prior_state', 'null']}

    timeseries = simulate_with_environment(compartment, settings)
    plot_simulation_output(timeseries, plot_settings, out_dir)
