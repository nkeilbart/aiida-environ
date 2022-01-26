from aiida_environ.calculations.energy_differentiate import calculate_finite_differences
from aiida.orm import Str, Int, Float, load_node

import pandas as pd

# *** LOAD COMPLETED WORKCHAIN ***

compare_forces_chain = load_node(1) # FIXME pick a CompareForcesWorkChain node
settings = compare_forces_chain.inputs.test_settings.attributes

n_steps = settings['nsteps']
diff_type = settings['diff_type']
diff_order = settings['diff_order']
step_sizes = settings['step_sizes']
atom = settings['atom_to_perturb']

dr = sum([component**2 for component in step_sizes]) ** 0.5

results = calculate_finite_differences(Int(n_steps), Float(dr), Str(diff_type), Str(diff_order))

# *** DISPLAY RESULTS ***

print()
print('atom number  = {}'.format(atom))
print('d{}           = {:.2f}'.format('x', step_sizes[0]))
print('d{}           = {:.2f}'.format('y', step_sizes[1]))
print('d{}           = {:.2f}'.format('z', step_sizes[2]))
print('difference   = {}-order {}'.format(diff_order, diff_type))
#print(f'environ     = {use_environ}')
#print(f'doublecell  = {double_cell}')
print()

print(pd.DataFrame(data=results.attributes))