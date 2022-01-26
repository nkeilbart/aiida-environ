from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain

from aiida.orm import Dict, Int, Float, Str, QueryBuilder
from aiida.engine import calcfunction

def _get_calculation_nodes():
    """Query database for EnvPwCalculation nodes"""

    # Get the last N EnvPwBaseWorkChains
    qb = QueryBuilder()
    qb.append(EnvPwBaseWorkChain)
    base_chains = qb.all(flat=True)[-N:]

    # Get Environ Calcs from WorkChains
    calcs = []
    for chain in base_chains:
        last_calc_of_chain = chain.called_descendants[-1]
        calcs.append(last_calc_of_chain)

    return calcs

def _calculate_first_order_difference(energies: tuple, force: float):
    """
    Returns first-order finite difference & compares to DFT force:
    finite difference = (energies[1] - energies[0]) / dr
    """

    dE = (energies[1] - energies[0]) / STEP
    return (dE, abs(dE - force))

def _calculate_second_order_difference(energies: tuple, forces: tuple):
    """
    Returns second-order finite difference & compares to force difference:
    finite difference = (energies[2] + 2*energies[1] - energies[0]) / dr**2
    """

    dE = (energies[2] + 2*energies[1] - energies[0]) / STEP**2
    dF = forces[1] - forces[0]
    return (dE, abs(dE - dF))

def _calculate_central_difference(i, order):
    """Returns first or second order central difference derivative"""

    if order == 'first':

        return _calculate_first_order_difference(
                    energies=(ENERGIES[i-1], ENERGIES[i+1]),
                    force=FORCES[i]
                )
    elif order == 'second':

        print('i:', i, 'ENERGIES:', ENERGIES)
        return _calculate_second_order_difference(
                    energies=(
                        ENERGIES[i-2],
                        ENERGIES[i],
                        ENERGIES[i+2]
                    ),
                    forces=(
                        FORCES[i-1],
                        FORCES[i+1]
                    )
                )

def _calculate_forward_difference(i, order):
    """Returns first or second order forward difference derivative"""

    if order == 'first':

        #print('\nENERGIES[i]:', ENERGIES[i], '\tENERGIES[i+1]:', ENERGIES[i+1])
        return _calculate_first_order_difference(
                    energies=(ENERGIES[i], ENERGIES[i+1]),
                    force=FORCES[i]
                )
    elif order == 'second':

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

def _calculate_backward_difference(i, order):
    """Returns first or second order backward derivative"""

    if order == 'first':

        return _calculate_first_order_difference(
            energies=(ENERGIES[i-1], ENERGIES[i]),
            force=FORCES[i]
        )

    elif order == 'second':

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

def _format_results(diff_type, diff_order):
    """Returns n-length energy and force lists for central difference results"""

    if diff_type == 'central':

        if diff_order == 'first':
            return [ENERGIES[i] for i in range(2, N-1, 2)], [FORCES[i] for i in range(2, N-1, 2)]

        elif diff_order == 'second':
            return [ENERGIES[i] for i in range(2, N, 4)], [FORCES[i] for i in range(2, N, 4)]

    elif diff_type == 'forward':
        return ENERGIES, FORCES[1:]

    else:
        return ENERGIES, FORCES[:-1]

@calcfunction
def calculate_finite_differences(n: Int, dr: Float, diff_type: Str, diff_order: Str) -> list:

    '''
    Compare DFT total force to numerical derivative dE/dr.
    
    Args:
        n:              aiida.orm.Int
        dr:             aiida.orm.Float
        diff_type:      aiida.orm.Str
        diff_order:     aiida.orm.Str

    Returns:
        differences: list
    '''

    global N
    global STEP
    global ENERGIES
    global FORCES

    N = n.value + 1 # include initial calculation

    calc_list = _get_calculation_nodes()

    STEP = dr.value
    ENERGIES = [calc.res.energy for calc in calc_list]
    FORCES = [calc.res.total_force for calc in calc_list]

    finite_forces = []
    differences = []

    # *** CALCULATE FINITE DIFFERENCE FORCES ***

    for i in range(N):

        if diff_type == 'central' and 0 < i < (N-1) and i % 2 == 0:
            if diff_order == 'second' and i == 0 or i == (N-2): continue
            else:
                dE, dF = _calculate_central_difference(i, diff_order)
                finite_forces.append(dE)
                differences.append(dF)

        elif diff_type == 'forward' and i < (N-1):
            if diff_order == 'second' and i == (N-2): continue
            else:
                dE, dF = _calculate_forward_difference(i, diff_order)
                finite_forces.append(dE)
                differences.append(dF)

        elif diff_type == 'backward' and i > 0:
            if diff_order == 'second' and i == 1: continue
            else:
                dE, dF = _calculate_backward_difference(i, diff_order)
                finite_forces.append(dE)
                differences.append(dF)

    # *** FORMAT & RETURN RESULTS ***
    
    ENERGIES, FORCES = _format_results(
            diff_type,
            diff_order
        )

    if diff_type == 'forward':
        finite_forces = finite_forces[1:]
        differences = differences[1:]

    elif diff_type == 'backward':
        finite_forces = finite_forces[:-1]
        differences = differences[:-1]

    results = Dict(dict={
                    "Environ": FORCES,
                    "Finite": finite_forces,
                    "\u0394F": differences
                })

    #data = Dict(dict={
    #        #"EnvPwCalculations": calc_list,
    #        "Energies": ENERGIES,
    #        })

    return results