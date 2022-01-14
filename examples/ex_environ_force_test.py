#from aiida.orm.nodes.data.upf import get_pseudos_from_structure # TO BE DEPRECATED - CONVENTION WILL BE USING AIIDA-PSEUDO PLUGIN
from aiida.orm.utils import load_code, load_group
from aiida.engine import submit
from aiida import load_profile
from aiida.orm import Dict

from aiida_quantumespresso.utils.resources import get_default_options


from make_inputs import *

load_profile()
sssp = load_group('SSSP/1.1/PBE/precision')

# try loading aiida-environ, everything stored as nodes already
code = load_code(5714)
builder = code.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw calcjob"
builder.metadata.options = get_default_options()
builder.settings = Dict(dict={'gamma_only': True}) # gamma k-point sampling

builder.structure = make_simple_structure()
builder.kpoints = make_simple_kpoints()
builder.parameters = make_simple_parameters()
builder.pseudos = sssp.get_pseudos(structure=builder.structure) # TODO take upffamily group string as input; if None, change structure to default structure & its pseudo
builder.environ_parameters = make_simple_environ_parameters()

calculation = submit(builder)
print(calculation)
