from __future__ import absolute_import, division, print_function

import os
import sys
import uuid
import argparse

from vivarium.core.emitter import timeseries_from_data
from vivarium.core.experiment import (
    generate_state,
    Experiment)
from vivarium.core.composition import (
    agent_environment_experiment,
    make_agents,
    simulate_experiment,
    plot_agents_multigen,
    process_in_compartment,
    EXPERIMENT_OUT_DIR,
)

# compartments
from vivarium.compartments.static_lattice import StaticLattice
from vivarium.compartments.chemotaxis_minimal import ChemotaxisMinimal
from vivarium.compartments.chemotaxis_master import ChemotaxisMaster

# processes
from vivarium.processes.Vladimirov2008_motor import MotorActivity
from vivarium.processes.multibody_physics import (
    agent_body_config,
)
from vivarium.plots.multibody_physics import plot_trajectory, plot_motility
from vivarium.processes.static_field import make_field


DEFAULT_BOUNDS = [400, 2000]
DEFAULT_AGENT_LOCATION = [0.5, 0.1]
DEFAULT_LIGAND_ID = 'MeAsp'
DEFAULT_INITIAL_LIGAND = 2.0
DEFAULT_ENVIRONMENT_TYPE = StaticLattice

MotorActivityAgent = process_in_compartment(MotorActivity)


def simulate_chemotaxis_experiment(
    agent_config=None,
    environment_config=None,
    initial_state=None,
    simulation_settings=None,
    experiment_settings=None):

    total_time = simulation_settings['total_time']
    timestep = simulation_settings['timestep']
    n_agents = simulation_settings['n_agents']

    # agents initial state
    agent_ids = [str(agent_id) for agent_id in range(n_agents)]
    agent_config['agent_ids'] = agent_ids
    initial_agent_body = agent_body_config({
        'bounds': DEFAULT_BOUNDS,
        'agent_ids': agent_ids,
        'location': DEFAULT_AGENT_LOCATION})
    initial_state.update(initial_agent_body)

    # make the experiment
    experiment = agent_environment_experiment(
        agent_config,
        environment_config,
        initial_state,
        experiment_settings)

    # simulate
    settings = {
        'total_time': total_time,
        'timestep': timestep,
        'return_raw_data': True}
    return simulate_experiment(experiment, settings)


def get_environment_config():
    # field parameters
    field_scale = 1.0
    exponential_base = 2e2
    field_center = [0.5, 0.0]

    # multibody process config
    multibody_config = {
        'animate': False,
        'jitter_force': 0.0,
        'bounds': DEFAULT_BOUNDS}

    # static field config
    field_config = {
        'molecules': [DEFAULT_LIGAND_ID],
        'gradient': {
            'type': 'exponential',
            'molecules': {
                DEFAULT_LIGAND_ID: {
                    'center': field_center,
                    'scale': field_scale,
                    'base': exponential_base}}},
        'bounds': DEFAULT_BOUNDS}

    return {
        'multibody': multibody_config,
        'field': field_config}



def plot_chemotaxis_experiment(data, field_config, filename):
    ## plots
    # multigen agents plot
    plot_settings = {
        'agents_key': 'agents',
        'max_rows': 30,
        'skip_paths': [
            ('boundary', 'mass'),
            ('boundary', 'length'),
            ('boundary', 'width'),
            ('boundary', 'location'),
        ]}
    plot_agents_multigen(data, plot_settings, out_dir, filename + '_agents')

    # trajectory and motility
    agents_timeseries = timeseries_from_data(data)
    field = make_field(field_config)
    trajectory_config = {
        'bounds': field_config['bounds'],
        'field': field}

    plot_trajectory(agents_timeseries, trajectory_config, out_dir, filename + '_trajectory')

    try:
        plot_motility(agents_timeseries, out_dir, filename + '_motility_analysis')
    except:
        print('plot_motility failed')


def run_mixed():
    filename = 'mixed'
    n_agents = 2
    total_time = 360
    timestep = 0.1
    compartment_config = {
        'ligand_id': DEFAULT_LIGAND_ID,
        'initial_ligand': DEFAULT_INITIAL_LIGAND,
        'external_path': ('global',),
        'agents_path': ('..', '..', 'agents')}

    # configure
    agent_config = [
        {
            'type': ChemotaxisMinimal,
            'number': 1,
            'config': compartment_config
        },
        {
            'type': MotorActivityAgent,
            'number': 1,
            'config': compartment_config
        }
    ]



    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_environment_config()}
    simulation_settings = {
        'n_agents': n_agents,
        'total_time': total_time,
        'timestep': timestep}

    # simulate
    data = simulate_chemotaxis_experiment(
        agent_config=agent_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, filename)


def run_minimal():
    filename = 'minimal'
    agent_type = ChemotaxisMinimal
    n_agents = 2
    total_time = 360
    timestep = 0.1
    compartment_config = {
        'ligand_id': DEFAULT_LIGAND_ID,
        'initial_ligand': DEFAULT_INITIAL_LIGAND,
        'external_path': ('global',),
        'agents_path': ('..', '..', 'agents')}

    # configure
    agent_config = {
        'type': agent_type,
        'config': compartment_config}
    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_environment_config()}
    simulation_settings = {
        'n_agents': n_agents,
        'total_time': total_time,
        'timestep': timestep}

    # simulate
    data = simulate_chemotaxis_experiment(
        agent_config=agent_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, filename)


def run_master():
    # TODO -- master requires environment for metabolism external

    filename = 'master'
    agent_type = ChemotaxisMaster
    n_agents = 1
    total_time = 30
    timestep = 0.1
    compartment_config = {
        'ligand_id': DEFAULT_LIGAND_ID,
        'initial_ligand': DEFAULT_INITIAL_LIGAND,
        'external_path': ('global',),
        'agents_path': ('..', '..', 'agents')}

    # configure
    agent_config = {
        'type': agent_type,
        'config': compartment_config}
    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_environment_config()}
    simulation_settings = {
        'n_agents': n_agents,
        'total_time': total_time,
        'timestep': timestep}

    # simulate
    data = simulate_chemotaxis_experiment(
        agent_config=agent_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, filename)


if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='multibody')
    parser.add_argument('--minimal', '-l', action='store_true', default=False)
    parser.add_argument('--master', '-m', action='store_true', default=False)
    parser.add_argument('--mixed', '-x', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.minimal or no_args:
        run_minimal()
    elif args.master:
        run_master()
    elif args.mixed:
        run_mixed()
