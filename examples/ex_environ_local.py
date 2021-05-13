from aiida import load_profile
load_profile()

from aiida.orm.utils import load_node, load_code
from aiida.engine import submit
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from . import node_assignment

# try loading aiida-environ, everything stored as nodes already
code = load_code()
builder = code.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.metadata.options.resources = {'num_machines': 1}
builder.metadata.options.max_wallclock_seconds = 30 * 60

environ_parameters = {
  "ENVIRON": {
      "env_surface_tension": 47.9,
      "env_pressure": -0.36,
      "environ_thr": 0.1,
      "env_static_permittivity": 78.3,
      "environ_type": 'input',
  },
  "BOUNDARY": {
      "rhomax": 0.005,
      "rhomin": 0.0001,
      "stype": 1,
      "solvent_mode": 'electronic',
  },
  "ELECTROSTATIC": {
      "tol": 1e-13,
  }
}

builder.structure = load_node(node_assignment.get("SIMPLE_STRUCTURE_PK"))
builder.kpoints = load_node(node_assignment.get("SIMPLE_KPOINTS_PK"))
builder.parameters = load_node(node_assignment.get("SIMPLE_PARAMETERS_PK"))
builder.pseudos = get_pseudos_from_structure(builder.structure, 'SSSPe')
builder.environ_parameters = environ_parameters

calculation = submit(builder)
print(calculation)
