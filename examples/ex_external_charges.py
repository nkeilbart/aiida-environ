from aiida import load_profile
load_profile()

from aiida.orm import Dict
from aiida.orm.utils import load_node, load_code
from aiida.engine import run
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import DataFactory
import node_assignment

# try loading aiida-environ, everything stored as nodes already
code = load_code(node_assignment.get("ENVIRON_CODE_PK"))
builder = code.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.metadata.dry_run = True

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

# this makes no sense but we'll create a dry run and check the environ.in file
EnvironChargeData = DataFactory('environ.charges')
charges = EnvironChargeData()
charges.append_charge(1, (0, 0, 0), 1.0, 0, 1)

builder.structure = load_node(node_assignment.get("SIMPLE_STRUCTURE_PK"))
builder.kpoints = load_node(node_assignment.get("SIMPLE_KPOINTS_PK"))
builder.parameters = load_node(node_assignment.get("SIMPLE_PARAMETERS_PK"))
builder.pseudos = get_pseudos_from_structure(builder.structure, 'SSSPe')
builder.environ_parameters = Dict(dict=environ_parameters)
builder.external_charges = charges

calculation = run(builder)
