#from aiida.orm.nodes.data.upf import get_pseudos_from_structure # TO BE DEPRECATED - CONVENTION WILL BE USING AIIDA-PSEUDO PLUGIN
from aiida.orm.utils import load_code, load_group
from aiida.engine import submit
from aiida import load_profile
from aiida.orm import Dict

from aiida_quantumespresso.utils.resources import get_default_options
from aiida_environ.workflows.pw.testF import ForceTestWorkChain, EnvPwBaseWorkChain


from make_inputs import *

load_profile()
#sssp = load_group('SSSP/1.1/PBE/precision')

# initialize force test workchain builder
builder = ForceTestWorkChain.get_builder()
builder.metadata.label = "environ force test example"
builder.metadata.description = "environ.pw force test workchain"

# base pw calculation setup
#builder.base.metadata.options = get_default_options()
#builder.base.settings = Dict(dict={'gamma_only': True}) # gamma k-point sampling
builder.base.code = load_code(1)
#builder.pw.structure = make_simple_structure()
builder.base.kpoints = make_simple_kpoints()
builder.base.parameters = make_simple_parameters()
#builder.pw.pseudos = sssp.get_pseudos(structure=builder.structure)
builder.base.environ_parameters = make_simple_environ_parameters()

# workchain setup
builder.structure = make_simple_structure()
builder.pseudo_group = 'SSSP/1.1/PBE/precision'
builder.test_settings = {
    'diff_type': 'central',
    'diff_order': 'first',
    'move_atom': 1,
    'nsteps': 5,
    'steplist': [0.0, 0.1, 0.0]
}

calculation = submit(builder)
print(calculation)
