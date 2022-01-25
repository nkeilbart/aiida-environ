from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain

from aiida.orm.utils import load_node
from aiida.orm import Dict, Float, Str, QueryBuilder
from aiida.engine import calcfunction

def _calculate_first_order_difference(energies: tuple, force: float, dr: float):
    """
    Returns first-order finite difference & compares to DFT force:
    finite difference = (energies[1] - energies[0]) / dr
    """

    dE = (energies[1] - energies[0]) / dr
    return (dE, abs(dE - force))

def _calculate_second_order_difference(energies: tuple, forces: tuple, dr: float):
    """
    Returns second-order finite difference & compares to force difference:
    finite difference = (energies[2] + 2*energies[1] - energies[0]) / dr**2
    """

    dE = (energies[2] + 2*energies[1] - energies[0]) / dr**2
    dF = forces[1] - forces[0]
    return (dE, abs(dE - dF))

@calcfunction
def calculate_finite_differences(dr: Float, diff_type: Str, diff_order: Str) -> list:

    '''
    Compare DFT total force to numerical derivative dE/dr.
    
    Args:
        pks:            aiida.orm.List
        dr:            aiida.orm.Float
        diff_type:       aiida.orm.Str
        diff_order:      aiida.orm.Str

    Returns:
        differences: list

    '''

    qb = QueryBuilder()
    qb.append(EnvPwBaseWorkChain)
    base_chains = qb.all(flat=True)
    
    calc_list = []
    for chain in base_chains:
        calc_list.append(chain.called_descendants[-1])

    energies = [calc.res.energy for calc in calc_list]
    dft_forces = [calc.res.total_force for calc in calc_list]
    fin_forces = []
    differences = []

    if diff_type == 'central':
        n = 2 * len(calc_list) # half & whole step calcs
    else:
        n = len(calc_list)

    for i in range(n):

        ith_E = energies[i]
        if i > 0:
            prev_E = energies[i-1]
        if i < (n-1):
            next_E = energies[i+1]

        if diff_type == 'central' and i > 0 and i % 2 == 0:

            if diff_order == 'first':

                dE, dF = _calculate_first_order_difference(
                    energies=(prev_E, next_E),
                    dr=dr.value,
                    force=dft_forces[i]
                )
            
            else:

                dE, dF = _calculate_second_order_difference(
                    energies=(next_E, ith_E, prev_E),
                    dr=dr.value,
                    forces=(dft_forces[i+1], dft_forces[i-1])
                )

        elif diff_type == 'forward':

            if diff_order == 'first' and i < n-2:

                dE, dF = _calculate_first_order_difference(
                    energies=(ith_E, next_E),
                    dr=dr.value,
                    force=dft_forces[i]
                )

            elif diff_order == 'second' and i < n-3:
                
                next2_E = energies[i+2]
                dE, dF = _calculate_second_order_difference(
                    energies=(ith_E, next_E, next2_E),
                    dr=dr.value,
                    forces=(dft_forces[i], dft_forces[i+1])
                )

        else:

            if diff_order == 'first' and  i > 0:

                dE = (ith_E - prev_E) / dr
                dE, dF = _calculate_first_order_difference(
                    energies=(prev_E, next_E),
                    dr=dr.value,
                    force=dft_forces[i]
                )

            elif diff_order == 'second' and i > 1:

                prev2_E = energies[i-2]
                dE, dF = _calculate_second_order_difference(
                    energies=(prev2_E, prev_E, ith_E),
                    dr=dr.value,
                    forces=(dft_forces[i-1], dft_forces[i])
                )

        fin_forces.append(dE)
        differences.append(dF)

    results = {
        #"EnvPwCalculations": calc_list,
        "Energies": energies,
        "Forces": dft_forces,
        "Calculated Forces": fin_forces,
        "Force Differences": differences
    }

    return Dict(dict=results) # TODO return DFT Fs & numerical Fs?