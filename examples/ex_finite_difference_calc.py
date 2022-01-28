from aiida_environ.calculations.finite import calculate_finite_differences
from aiida.orm import load_node, List, Bool

# TODO query for CompareForcesWorkChain

ParentChain = load_node(5044) # FIXME need to select a CompareForcesWorkChain node
BaseChains = [chain.pk for chain in ParentChain.called[:-1]]

results = calculate_finite_differences(
    List(list=BaseChains),
    ParentChain.inputs.test_settings,
    Bool(True)
)