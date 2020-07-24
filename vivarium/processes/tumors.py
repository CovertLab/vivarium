from __future__ import absolute_import, division, print_function

import os
import sys
import copy
import random
import argparse

from vivarium.library.units import units
from vivarium.library.dict_utils import deep_merge
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)
from vivarium.core.process import Generator
from vivarium.processes.meta_division import MetaDivision


NAME = 'Tumor'


class TumorProcess(Process):
    """Tumor process with 2 states

    States:
        - PDL1p (PDL1+, MHCI+)
        - PDL1n (PDL1-, MHCI-)

    Required parameters:
        -

    Target behavior:

    TODOs
        - make this work!
    """

    name = 'Tumor'
    defaults = {
        'diameter': 20 * units.um,
        'initial_PDL1n': 1.0,
        #TODO - @Eran How do I initialize number of cells in grid (I have this data for both)
        #   We may not need this now, but thought about this as a parameter
        #TODO - @Eran - Some of the parameters for different states is the same value.
        #   Do I need separate parameters for each state if it is the same value?
        # e.g. death/migration for both states

        # death rates
        'death_PDL1p': 2e-5,  # fairly negligible compared to growth/killing
        'death_PDL1n': 2e-5,  # same for above

        # division rate
        'PDL1n_growth': 0.3,  # probability of division in 8 hours - 1/24 hr (Eden, 2011)
        #'PDL1p_growth': 0,  # Cells arrested - do not divide (data, Thibaut 2020, Hoekstra 2020)

        # migration
        'PDL1n_migration': 0.25,  # um/minute (Weigelin 2012)
        'PDL1p_migration': 0.25,   # um/minute (Weigelin 2012)

        # settings
        'self_path': tuple(),
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}
        parameters = copy.deepcopy(self.defaults)
        deep_merge(parameters, initial_parameters)
        super(TumorProcess, self).__init__(parameters)

        if random.uniform(0, 1) < self.defaults['initial_PDL1n']:
            self.initial_state = 'PDL1n'
        else:
            self.initial_state = 'PDL1p'

        self.self_path = self.or_default(
            initial_parameters, 'self_path'
        )

    def ports_schema(self):
        return {
            'globals': {
                'divide': {
                    '_default': False,
                    '_updater': 'set'}
            },
            'internal': {
                'cell_state': {
                    '_default': self.initial_state,
                    '_emit': True,
                    '_updater': 'set'
                }
            },
            'boundary': {
                'diameter': {
                    '_default': self.parameters['diameter']
                },
                'PDL1': {
                    '_default': 0,
                    '_emit': True,
                    '_updater': 'accumulate',
                },
                'MHCI': {
                    '_default': 0,
                    '_emit': True,
                    '_updater': 'set',
                },  # membrane protein, promotes Tumor death
            },
            'neighbors': {
                'PD1': {
                    '_default': 0,
                    '_emit': True,
                },
                #TODO - @Eran - like the t_cell process, I am still a little uncertain how to connect
                #   where the 2 processes interact. Is this where the IFNg and cytotoxic packets
                #   from the t_cell process would come in?
            }
        }

    def next_update(self, timestep, states):
        cell_state = states['internal']['cell_state']

        # death
        if cell_state == 'PDL1n':
            if random.uniform(0, 1) < self.parameters['death_PDL1n'] * timestep:
                print('PDL1n DEATH!')
                return {
                    '_delete': {
                        'path': self.self_path
                    }
                }

        elif cell_state == 'PDL1p':
            if random.uniform(0, 1) < self.parameters['death_PDL1p'] * timestep:
                print('PDL1p DEATH!')
                return {
                    '_delete': {
                        'path': self.self_path
                    }
                }

        # division
        if cell_state == 'PDL1n':
            if random.uniform(0, 1) < self.parameters['PDL1n_growth'] * timestep:
                print('PDL1n DIVIDE!')
                return {
                    'globals': {
                        'divide': True
                    }
                }
        elif cell_state == 'PDL1p':
            pass

        #TODO - @Eran - Is there a way to stop simulation if tumor cells reach 5x10^5 total?

        # state transition
        new_cell_state = cell_state
        if cell_state == 'PDL1n':
            #TODO - if IFNg > 1 ng/mL begin switch to PDL1p -
            #   target effect 300 um radius around T cells after 40 h
            #   requires at least 6 h of contact with this conc.
            #   @Eran - it seems from all my research that tumor cells require a certain amount of
            #       IFNg present for at least between 6-12 h and then the switch happens completely
            #       by 24 h. Is there a way to start a timer for this? One thing I thought was that we
            #       could start a constant production of MHCI and PDL1 from the moment of contact and then
            #       once those values are above 50,000 then we could switch but not so physiological.
            #       The dynamics psrobably come from some delay of transcription factor pathways, but I
            #       am not really interested right now in that level of detail (maybe someday :))
            #TODO - @Eran - How do I reference the environment - i.e. the number of IFNg molecules present
            #   directly overlapping with the cancer cell to make this change?
            pass
        elif cell_state == 'PDL1p':
            pass

        # behavior
        MHCI = 0
        PDL1 = 0

        # TODO migration - Can do this once I learn

        # TODO death by killing (at end of time step?)
        if new_cell_state == 'PDL1n':
            #TODO - if cytotoxic packets >128 then cell is dead - 120 minute delay
            # @Eran - If I reference cytotoxic packets above, then can I reference them here?
            # See other comments about referencing parameters from other processes
            pass
        elif new_cell_state == 'PDL1p':
            #TODO - if cytotoxic packets >128 then cell is dead - 120 minute delay
            # @Eran - if this parameter of death is the same for both states, do I need to
            # specify both like this?
            pass

        return {
            'internal': {
                'cell_state': new_cell_state
            },
            'boundary': {
                'MHCI': MHCI,
                'PDL1': PDL1,
                #TODO - @Eran - Based on my research, the expression of these ligands is dynamic
                # and slowly grows the first 6 hours and then dramatically increases the next
                # 6-12 h and plateaus once they reach their state. We do not necessarily need
                # that in my opinion for the ligands, but the dealy may be nice for the phenotype
                # switch. What do you think?
            },
        }



class TumorCompartment(Generator):

    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('..', '..', 'agents',),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = config
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value

        # paths
        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])

    def generate_processes(self, config):
        daughter_path = config['daughter_path']
        agent_id = config['agent_id']

        division_config = dict(
            config.get('division', {}),
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)

        Tumor = TumorProcess(config.get('growth', {}))
        division = MetaDivision(division_config)

        return {
            'Tumor': Tumor,
            'division': division}

    def generate_topology(self, config):
        return {
            'Tumor': {
                'internal': ('internal',),
                'boundary': self.boundary_path,
                'global': self.boundary_path},
            'division': {
                'global': self.boundary_path,
                'cells': self.agents_path},
            }


def get_PD1_timeline():
    timeline = [
        (0, {('neighbors', 'PD1'): 0.0}),
        (10, {('neighbors', 'PD1'): 1.0}),
        (20, {('neighbors', 'PD1'): 0.0}),
        (30, {}),
    ]
    return timeline

def test_single_Tumor(
        total_time=20,
        timeline=None,
        out_dir='out'):

    Tumor_process = TumorProcess({})

    if timeline is not None:
        settings = {
            'timeline': {
                'timeline': timeline}}
    else:
        settings = {'total_time': total_time}

    # run experiment
    timeseries = simulate_process_in_experiment(Tumor_process, settings)

    # plot
    plot_settings = {}
    plot_simulation_output(timeseries, plot_settings, out_dir)


def run_batch_Tumor(out_dir='out'):
    import ipdb; ipdb.set_trace()
    pass

if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='tumor cells')
    parser.add_argument('--single', '-s', action='store_true', default=False)
    parser.add_argument('--timeline', '-t', action='store_true', default=False)
    parser.add_argument('--batch', '-b', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    total_time = 1000
    if args.single or no_args:
        test_single_Tumor(
            total_time=total_time,
            out_dir=out_dir)

    if args.timeline:
        timeline = get_PD1_timeline()
        test_single_Tumor(
            timeline=timeline,
            out_dir=out_dir)

    if args.batch:
        run_batch_Tumor(
            out_dir=out_dir,
            total_time=total_time)
