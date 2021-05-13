from aiida.orm.utils import load_node, load_code
from aiida.engine import submit
from aiida.orm import Dict
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import WorkflowFactory
import node_assignment

# Once this runs right, just comment out dicts and load_node
# try loading aiida-environ, everything stored as nodes already
code = load_code(109)
workchain = WorkflowFactory('environ.pw.solvation')
builder = workchain.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.pw.metadata.options.resources = {'num_machines': 1}
builder.pw.metadata.options.max_wallclock_seconds = 30 * 60
builder.pw.code = code

environ_parameters = {
    "ENVIRON": {
        "environ_restart": False,
        "env_electrostatic": True,
        "environ_thr": 0.1
    },                                                   
    "BOUNDARY": {
        "alpha": 1.12,
        "radius_mode": "muff",
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

builder.pw.structure = load_node(node_assignment.get("SIMPLE_STRUCTURE_PK"))
builder.pw.kpoints = load_node(node_assignment.get("SIMPLE_KPOINTS_PK"))
builder.pw.parameters = load_node(node_assignment.get("SIMPLE_PARAMETERS_PK"))
builder.pw.pseudos = get_pseudos_from_structure(builder.structure, 'SSSPe')
builder.pw.environ_parameters = Dict(dict=environ_parameters)
builder.environ_vacuum = Dict(dict=environ_vacuum)
builder.environ_solution = Dict(dict=environ_solution)

print(builder)
calculation = submit(builder)