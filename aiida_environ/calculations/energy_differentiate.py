from numpy import disp
from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain

from aiida.orm import Dict, List, Float, Str, load_node
from aiida.engine import calcfunction

import pandas

def setup(base_chains, dh):
    """Returns initial position data and initializes global variables."""

    global N
    global STEP
    global ENERGIES
    global FORCES

    # TODO would like to use base workchain output, but energy, force precision is slightly different
    # WorkChain.outputs.output_trajectory.get_array('energy')[0]
    # WorkChain.outputs.output_trajectory.get_array('total_force')[0]

    # Get Environ Calcs from WorkChains
    calcs = []
    for chain in base_chains:
        last_calc_of_chain = load_node(chain).called_descendants[-1]
        calcs.append(last_calc_of_chain)

    N = len(base_chains)
    STEP = dh
    ENERGIES = [calc.res.energy for calc in calcs]
    FORCES = [calc.res.total_force for calc in calcs]

    return {'Energy': ENERGIES[0], 'Total force': FORCES[0]}

def _calculate_first_order_difference(energies: tuple, force: float):
    """Returns first-order finite difference & compares to DFT force."""

    dE = (energies[1] - energies[0]) / STEP
    return dE, abs(dE - force)

def _calculate_second_order_difference(energies: tuple, forces: tuple):
    """Returns second-order finite difference & compares to force difference."""

    dE = (energies[2] - 2*energies[1] + energies[0]) / STEP**2
    dF_DFT = forces[1] - forces[0]

    DFT_FORCE_DIFFERENCES.append(dF_DFT)

    return dE, abs(dE - dF_DFT)

def _calculate_central_difference(i, order):
    """Returns first or second order central difference derivative."""

    if order == 'second':

        return _calculate_second_order_difference(
                    energies=(
                        ENERGIES[i-1],
                        ENERGIES[i],
                        ENERGIES[i+1]
                    ),
                    forces=(
                        FORCES[i-1],
                        FORCES[i+1]
                    )
                )

    return _calculate_first_order_difference(
            energies=(ENERGIES[i-1], ENERGIES[i+1]),
            force=FORCES[i]
        )

def _calculate_forward_difference(i, order):
    """Returns first or second order forward difference derivative."""
        
    if order == 'second':

        return _calculate_second_order_difference(
                    energies=(
                        ENERGIES[i],
                        ENERGIES[i+1],
                        ENERGIES[i+2]
                    ),
                    forces=(
                        FORCES[i],
                        FORCES[i+1]
                    )
                )
    
    return _calculate_first_order_difference(
                energies=(ENERGIES[i], ENERGIES[i+1]),
                force=FORCES[i]
            )

def _calculate_backward_difference(i, order):
    """Returns first or second order backward difference derivative."""

    if order == 'second':

        return _calculate_second_order_difference(
                energies=(
                    ENERGIES[i-2],
                    ENERGIES[i-1],
                    ENERGIES[i]
                ),
                forces=(
                    FORCES[i-1],
                    FORCES[i]
                )
            )
    
    return _calculate_first_order_difference(
                energies=(ENERGIES[i-1], ENERGIES[i]),
                force=FORCES[i]
            )

def _format_results(diff_type, diff_order):
    """Returns modified-length DFT energy and force lists."""

    if diff_order == 'second':
        return ENERGIES, DFT_FORCE_DIFFERENCES

    if diff_type == 'central':
        return [ENERGIES[i] for i in range(1, N, 2)], [FORCES[i] for i in range(2, N-1, 2)]
    elif diff_type == 'forward':
        return ENERGIES, FORCES[:-1]
    else:
        return ENERGIES, FORCES[1:]

def _display_results(params, dft_forces, finite_forces, force_differences):
    """Displays finite differences against forces and compares them."""

    print()
    print('atom number  = {}'.format(params['atom_to_perturb']))
    print('n-steps      = {}'.format(params['n_steps']))
    print('d{}           = {:.2f}'.format('x', params['step_sizes'][0]))
    print('d{}           = {:.2f}'.format('y', params['step_sizes'][1]))
    print('d{}           = {:.2f}'.format('z', params['step_sizes'][2]))
    print('difference   = {}-order {}'.format(params['diff_order'], ['diff_type']))
    #print(f'environ     = {use_environ}')
    #print(f'doublecell  = {double_cell}')
    print()

    print(dft_forces)
    print(finite_forces)
    print(force_differences)
    print()

    display = {
        "Environ": dft_forces,
        "Finite": finite_forces,
        "\u0394F": force_differences
    }

    print(pandas.DataFrame(
        data=display,
        index=[i for i in range(1, len(finite_forces)+1)])
    )

@calcfunction
def calculate_finite_differences(chain_list: List, test_settings: Dict) -> Dict:
    """
    Returns finite differences based on the WorkChain node PKs and test settings passed.
    
    Inputs:
        chain_list:     aiida.orm.List
        test_settings:  aiida.orm.Dict

    Outputs:
        data:        aiida.orm.Dict
    """

    settings = test_settings.get_dict()

    dr = sum([component**2 for component in settings['step_sizes']]) ** 0.5
    diff_type = settings['diff_type']
    diff_order = settings['diff_order']
    initial = setup(chain_list.get_list(), dr)

    if diff_order == 'second':
        global DFT_FORCE_DIFFERENCES
        DFT_FORCE_DIFFERENCES = []

    finites = []
    differences = []

    # *** CALCULATE FINITE DIFFERENCES ***

    for i in range(N):

        if diff_type == 'central' and 0 < i < (N-1):

            if diff_order == 'first' and i % 2 == 0:
                dE, dF = _calculate_central_difference(i, diff_order)
            else:
                dE, dF = _calculate_central_difference(i, diff_order)
            
            finites.append(dE)
            differences.append(dF)

        elif diff_type == 'forward' and i < (N-1):

            if diff_order == 'second' and i == (N-2):
                continue
            else:
                dE, dF = _calculate_forward_difference(i, diff_order)
                finites.append(dE)
                differences.append(dF)

        elif diff_type == 'backward' and i > 0:

            if diff_order == 'second' and i == 1:
                continue
            else:
                dE, dF = _calculate_backward_difference(i, diff_order)
                finites.append(dE)
                differences.append(dF)

    # *** DISPLAY & RETURN RESULTS ***
    
    energies, forces = _format_results(
            diff_type,
            diff_order
        )

    # FIXME aiida will not display print() lines during WorkChains
    # TODO write DataFrame and/or plot as SinglefileData and return with key in data dict?
    _display_results(settings, forces, finites, differences)

    data = Dict(dict={
                    "Initial position": initial,
                    "Environ energies": energies,
                    "Environ forces": forces,
                    "Finite forces": finites,
                    "Delta": differences
                })

    return data