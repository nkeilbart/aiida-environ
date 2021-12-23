from aiida.orm.utils import load_node, load_code
from aiida.engine import submit
from aiida.orm import Dict, List
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import WorkflowFactory
import node_assignment
from query import solvent_structs, struct_and_dict
import pdb

#===VARIABLES===#
ALPHA   = 1.14
BETA    = -0.10
GAMMA   = 5
EPSILON = 9.8629
#===============#

code = load_code(10727)
dicts = solvent_structs('octanol', 10)
structure_pks = []
expt_energy_vals = []
for d in dicts:
    structure_pks.append(d.attributes['solute'])
    expt_energy_vals.append(d.attributes['deltagsolv'])
workchain = WorkflowFactory('environ.pw.pworkchain')
builder = workchain.get_builder()

builder.structure_pks = List(list=structure_pks)
builder.expt_energy_vals = List(list=expt_energy_vals)

builder.metadata.label = "PWorkchain Test"
builder.metadata.description = "Test of environ plugin"
builder.base.pw.metadata.options.resources = {'num_machines': 1}
builder.base.pw.metadata.options.max_wallclock_seconds = 30 * 60
builder.base.pw.code = code
# builder.base.pw.metadata.options.account = "pi_mbn0025" # Account name
builder.base.pw.metadata.options.queue_name = "production"
builder.base.pw.metadata.options.qos = "general"

environ_parameters = {
    "ENVIRON": {
        "environ_restart": False,
        "env_electrostatic": True,
        "environ_thr": 0.1,
        'verbose': 1
    },                                                   
    "BOUNDARY": {
        "alpha": ALPHA,
        "solvent_mode": "ionic"
    },
    "ELECTROSTATIC": {
        "tol": 1e-10
    }                           
}    
environ_vacuum = {
    "ENVIRON": {
        "environ_type": "input",
        "env_pressure": BETA, # Beta 
        "env_static_permittivity": 1.,
        "env_surface_tension": GAMMA # Gamma
    }
}
environ_solution = {
    "ENVIRON": {
        "environ_type": "input",
        "env_pressure": BETA,
        "env_static_permittivity": EPSILON,
        "env_surface_tension": GAMMA
    }
}             

# builder.base.structure = load_node(node_assignment.get("SIMPLE_STRUCTURE_PK"))
builder.base.pw.kpoints = load_node(node_assignment.get("SIMPLE_KPOINTS_PK"))
builder.base.pw.parameters = load_node(node_assignment.get("SIMPLE_PARAMETERS_PK"))
# builder.base.pseudos = get_pseudos_from_structure(builder.pw.structure, 'SSSP')
builder.base.pw.environ_parameters = Dict(dict=environ_parameters)
builder.base.environ_vacuum = Dict(dict=environ_vacuum)
builder.base.environ_solution = Dict(dict=environ_solution)

print(builder)
calculation = submit(builder)