from aiida import load_profile
load_profile()

from aiida.orm.utils import load_code
from aiida.engine import submit
from aiida.orm.nodes.data.upf import get_pseudos_from_structure

from aiida_quantumespresso.utils.resources import get_default_options

from make_inputs import *

# try loading aiida-environ, everything stored as nodes already
#code = load_code(5714)
code = load_code(8536) # Nicholas machine
builder = code.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw calcjob"
builder.metadata.options = get_default_options()

builder.structure = make_organic_structure()
builder.kpoints = make_simple_kpoints()
builder.parameters = make_simple_parameters()
#builder.pseudos = get_pseudos_from_structure(builder.structure, 'SSSPe')
builder.pseudos = get_pseudos_from_structure(builder.structure, 'SSSP') # Nicholas machine
builder.environ_parameters = make_simple_environ_parameters()

calculation = submit(builder)
print(calculation)
