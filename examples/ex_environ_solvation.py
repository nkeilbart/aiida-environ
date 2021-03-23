from aiida.orm.utils import load_node, load_code
from aiida.engine import submit, run
from aiida.orm import Dict
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import WorkflowFactory
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
structure = load_node(284)
pp_water = get_pseudos_from_structure(structure, 'SSSPe')
kpoints = load_node(285)
parameters = {
    "CONTROL": {
        "calculation": "scf",
        "restart_mode": "from_scratch",
        "tprnfor": True
    },
    'SYSTEM': {
        'ecutrho': 300,
        'ecutwfc': 30
    }, 
    'ELECTRONS': {
        'conv_thr': 5.e-9,
        'diagonalization': 'cg',
        'mixing_beta': 0.4,
        'electron_maxstep': 200
    }
}
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
builder.pw.structure = structure
builder.pw.kpoints = kpoints
builder.pw.parameters = Dict(dict=parameters)
builder.pw.pseudos = pp_water
builder.pw.environ_parameters = Dict(dict=environ_parameters)
builder.environ_vacuum = Dict(dict=environ_vacuum)
builder.environ_solution = Dict(dict=environ_solution)
print(builder)
calculation = submit(builder)