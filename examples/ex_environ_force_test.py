#from aiida.orm.nodes.data.upf import get_pseudos_from_structure # TO BE DEPRECATED - CONVENTION WILL BE USING AIIDA-PSEUDO PLUGIN
from aiida.orm.utils import load_code, load_group
from aiida.engine import submit
from aiida import load_profile
from aiida.orm import Dict, Str

from aiida_environ.workflows.pw.compare_forces import FiniteForcesWorkChain
from aiida_quantumespresso.utils.resources import get_default_options

from make_inputs import *

load_profile()
sssp = load_group('SSSP/1.1/PBE/precision')

# initialize force test workchain builder
builder = FiniteForcesWorkChain.get_builder()
builder.metadata.label = "environ force test example"
builder.metadata.description = "environ.pw force test workchain"

# base pw calculation setup
#builder.base.pw.metadata.options = get_default_options()
#builder.base.pw.settings = Dict(dict={'gamma_only': True}) # gamma k-point sampling
builder.base.kpoints = make_simple_kpoints()
builder.base.pw.code = load_code(1)
builder.base.pw.parameters = make_simple_parameters()
builder.base.pw.environ_parameters = make_simple_environ_parameters()

# workchain setup
builder.structure = make_simple_structure()
builder.test_settings = Dict(dict={
    'diff_type': 'central',
    'diff_order': 'first',
    'atom_to_move': 1,
    'nsteps': 2,
    'step_sizes': [0.0, 0.1, 0.0]
})

calculation = submit(builder)
#print(calculation)
