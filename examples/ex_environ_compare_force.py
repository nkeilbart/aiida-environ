#from aiida.orm.nodes.data.upf import get_pseudos_from_structure # TO BE DEPRECATED - CONVENTION WILL BE USING AIIDA-PSEUDO PLUGIN
from aiida.orm.utils import load_code, load_group
from aiida.engine import submit
from aiida import load_profile
from aiida.orm import Dict, Str

from aiida_environ.workflows.pw.compare_forces import CompareForcesWorkChain
from aiida_quantumespresso.utils.resources import get_default_options

from make_inputs import *

load_profile()

inputs = {
    'structure': make_simple_structure(),
    'pseudo_group': Str('SSSP/1.1/PBE/precision'),
    'test_settings': Dict(dict={
        'diff_type': 'forward',
        'diff_order': 'first',
        'atom_to_perturb': 1,
        'nsteps': 2,
        'step_sizes': [0.0, 0.1, 0.0]
    }),
    'base': {
        'pw': {
            'code': load_code(1),
            'parameters': make_simple_parameters(),
            'environ_parameters': make_simple_environ_parameters(),
            'metadata': {
                'options': get_default_options()
            }
        },
        'kpoints': make_simple_kpoints()

    },
    'metadata': {
        'label': "finite difference chain example w/ environ base chain",
        'description': "environ.pw force test workchain"
    }
}

calculation = submit(FiniteForcesWorkChain, **inputs)
print(calculation)
