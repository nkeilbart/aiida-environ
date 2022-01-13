from aiida.engine import calcfunction
from aiida.plugins import DataFactory
from aiida.orm import Dict
from aiida.orm.utils import load_node


@calcfunction
def calc_partial(nstruct, delta, expt_energy, calculations):
    """Calculate partial derivatives for solvation energy parameterization

    Args:
        aiida.orm.Int: Number of Structures
        aiida.orm.Float: Delta value to increment alpha
        aiida.orm.List: Experimental Energies
        aiida.orm.Dict: Calculation PKs

    Returns:
        aiida.orm.Dict: Mean Squared Error for alpha, partial for alpha, partial for beta, partial for gamma
    """
    #=== Hardcoded values ===#
    learning_gamma = 1e-2
    learning_beta = 1e-3
    learning_alpha = -5e-3
    #========================#

    # 0 is the solvation energy for param = param0, 1 is the solvation energy for param = param0 + dparam
    n = nstruct.value
    solvation_energy_0 = [0.0] * n
    solvation_energy_1 = [0.0] * n
    qm_surface = [0.0] * n
    qm_volume = [0.0] * n

    # calculate and store the solvation energy
    for i in range(n):
        node_vac = load_node(calculations[f'vacuum_{i}'])
        node_sol_0 = load_node(calculations[f'solution_0_{i}'])
        if node_sol_0.exit_status > 0:
            #self.report(f'simulation {node_sol_0.pk} did not complete successfully, skipping structure...')
            continue
        node_sol_1 = load_node(calculations[f'solution_1_{i}'])
        if node_sol_1.exit_status > 0:
            #self.report(f'simulation {node_sol_1.pk} did not complete successfully, skipping structure...')
            continue
        solvation_energy_0[i] += (
            node_sol_0.outputs.output_parameters['energy'] - node_vac.outputs.output_parameters['energy'])
        solvation_energy_1[i] += (
            node_sol_1.outputs.output_parameters['energy'] - node_vac.outputs.output_parameters['energy'])
        qm_surface[i] = node_sol_0.outputs.output_parameters['qm_surface'][-1]
        qm_volume[i] = node_sol_0.outputs.output_parameters['qm_volume'][-1]

    # calculate partials
    grad_gamma = 0.0
    grad_beta = 0.0
    mse0 = 0.0
    mse1 = 0.0
    solvation_energy_expt = expt_energy.get_list()

    for i in range(n):
        grad_gamma += (solvation_energy_0[i] - solvation_energy_expt[i]) * qm_surface[i] * 2.0 / n
        grad_beta += (solvation_energy_0[i] - solvation_energy_expt[i]) * qm_volume[i] * 2.0 / n
        mse0 += (solvation_energy_0[i] - solvation_energy_expt[i]) ** 2 / n
        mse1 += (solvation_energy_1[i] - solvation_energy_expt[i]) ** 2 / n

    grad_alpha = (mse1 - mse0) / delta.value

    result = {
        'mse': mse0,
        'grad_alpha': grad_alpha,
        'grad_beta': grad_beta,
        'grad_gamma': grad_gamma
    }

    return Dict(dict=result)