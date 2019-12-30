from __future__ import absolute_import, division, print_function

import os

from lens.processes.metabolism import Metabolism
from lens.environment.make_media import Media
from lens.utils.units import units

DATA_FILE = os.path.join('models', 'e_coli_core.json')
# TODO -- to load additional BiGG models requires adding their external_molecules in a new media.
# DATA_FILE = os.path.join('models', 'iJR904.json')

def BiGGMetabolism(parameters):
    initial_state = get_initial_state()

    parameters['model_path'] = parameters.get('model_path', DATA_FILE)
    parameters['initial_state'] = parameters.get('initial_state', initial_state)

    return Metabolism(parameters)

def get_initial_state():
    # internal state
    mass = 1339 * units.fg
    density = 1100 * units.g/units.L
    volume = mass.to('g') / density
    internal = {
            'mass': mass.magnitude,  # fg
            'volume': volume.magnitude}

    # external state
    make_media = Media()
    external = make_media.get_saved_media('ecoli_core_GLC')

    return {
        'internal': internal,
        'external': external}

def kinetic_rate(mol_id, vmax, km=0.0):
    def rate(state):
        flux = (vmax * state[mol_id]) / (km + state[mol_id])
        return flux
    return rate

def toy_transport_kinetics():
    transport_kinetics = {
        "GLCpts": kinetic_rate('glc__D_e', 1.5e0, 5),  # glucose mmol/L/s
    }
    return transport_kinetics

def test_metabolism():
    # configure process
    metabolism = BiGGMetabolism({})

    print('MODEL: {}'.format(metabolism.fba.model))
    print('REACTIONS: {}'.format(metabolism.fba.model.reactions))
    print('METABOLITES: {}'.format(metabolism.fba.model.metabolites))
    print('GENES: {}'.format(metabolism.fba.model.genes))
    print('COMPARTMENTS: {}'.format(metabolism.fba.model.compartments))
    print('SOLVER: {}'.format(metabolism.fba.model.solver))
    print('EXPRESSION: {}'.format(metabolism.fba.model.objective.expression))

    print(metabolism.fba.optimize())
    print(metabolism.fba.model.summary())
    print('internal: {}'.format(metabolism.fba.internal_reactions()))
    print('external: {}'.format(metabolism.fba.external_reactions()))
    print(metabolism.fba.reaction_ids())
    print(metabolism.fba.get_reactions())
    print(metabolism.fba.get_reaction_bounds())
    print(metabolism.fba.read_exchange_fluxes())


if __name__ == '__main__':
    from lens.processes.metabolism import simulate_metabolism, save_network
    from lens.actor.process import convert_to_timeseries, plot_simulation_output

    out_dir = os.path.join('out', 'tests', 'BiGG_metabolism')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # add toy transport to config
    toy_config = {}
    toy_transport = toy_transport_kinetics()
    toy_config['constrained_flux_ids'] = toy_transport.keys()

    # get ecoli core metabolism model
    ecoli_core_metabolism = BiGGMetabolism(toy_config)

    # simulate model
    simulation_config = {
        'process': ecoli_core_metabolism,
        'total_time': 1000,
        'transport_kinetics': toy_transport_kinetics(),
        'environment_volume': 5e-13}

    plot_settings = {}
        # 'skip_roles': ['exchange'],
        # 'overlay': {
        #     'reactions': 'flux_bounds'}}

    saved_data = simulate_metabolism(simulation_config)
    timeseries = convert_to_timeseries(saved_data)
    plot_simulation_output(timeseries, plot_settings, out_dir)

    # make flux network from model
    save_network(ecoli_core_metabolism, 10, out_dir)
