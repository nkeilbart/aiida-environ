from aiida.orm.utils import load_code
from aiida.engine import submit
from aiida.orm import Dict
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import WorkflowFactory

from aiida_quantumespresso.utils.resources import get_default_options

from make_inputs import *

# Once this runs right, just comment out dicts and load_node
# try loading aiida-environ, everything stored as nodes already
code = load_code(5714)
workchain = WorkflowFactory('environ.pw.solvation')
builder = workchain.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw solvation workflow"
builder.metadata.options = get_default_options()

environ_parameters = {
    "ENVIRON": {
        "environ_restart": False,
        "env_electrostatic": True,
        "environ_thr": 0.1
    },                                                   
    "BOUNDARY": {
        "alpha": 1.12,
        "solvent_mode": "ionic"
    },
    "ELECTROSTATIC": {
        "tol": 1e-10
    }                           
}    
environ_vacuum = {
    "ENVIRON": {
        "environ_type": "input",
        "env_pressure": 0.,
        "env_static_permittivity": 1.,
        "env_surface_tension": 0.
    }
}
environ_solution = {
    "ENVIRON": {
        "environ_type": "input",
        "env_pressure": -0.35,
        "env_static_permittivity": 78.3,
        "env_surface_tension": 50
    }
}              

builder.pw.structure = make_organic_structure()
builder.pw.kpoints = make_simple_kpoints()
builder.pw.parameters = make_simple_parameters()
builder.pw.pseudos = get_pseudos_from_structure(builder.pw.structure, 'SSSPe')
builder.pw.environ_parameters = Dict(dict=environ_parameters)
builder.environ_vacuum = Dict(dict=environ_vacuum)
builder.environ_solution = Dict(dict=environ_solution)

print(builder)
calculation = submit(builder)