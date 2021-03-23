from aiida import load_profile
load_profile()

from aiida.orm.utils import load_node, load_code
from aiida.orm import Dict
from aiida.engine import run
from aiida.engine import submit

# try loading aiida-environ, everything stored as nodes already
code = load_code(109)
builder = code.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.metadata.options.resources = {'num_machines': 1}
builder.metadata.options.max_wallclock_seconds = 30 * 60

structure = load_node(2)
pp_si = load_node(38)
kpoints = load_node(88)
parameters = load_node(124)
environ_parameters = load_node(134)
#environ_parameters = {
#   "ENVIRON": {
#       "env_surface_tension": 47.9,
#       "env_pressure": -0.36,
#       "environ_thr": 0.1,
#       "env_static_permittivity": 78.3,
#       "environ_type": 'input',
#   },
#   "BOUNDARY": {
#       "rhomax": 0.005,
#       "rhomin": 0.0001,
#       "stype": 1,
#       "solvent_mode": 'electronic',
#   },
#   "ELECTROSTATIC": {
#       "tol": 1e-13,
#   }
#}

builder.structure = structure
builder.kpoints = kpoints
builder.parameters = parameters
builder.pseudos = {'Si': pp_si}
builder.environ_parameters = environ_parameters

calculation = submit(builder)
print(calculation)
