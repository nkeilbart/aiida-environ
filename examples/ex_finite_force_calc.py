from aiida_environ.calculations.energy_differentiate import calculate_finite_differences
from aiida_environ.workflows.pw.compare_forces import CompareForcesWorkChain
from aiida.orm import load_node, List

# TODO query for CompareForcesWorkChain

ParentChain = load_node(4100)
BaseChains = [chain.pk for chain in ParentChain.called[:-1]]

results = calculate_finite_differences(
    List(list=BaseChains),
    ParentChain.inputs.test_settings
)