from aiida.orm.utils import load_node, load_code
from aiida.engine import submit
from aiida.orm import List, Dict, StructureData
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import WorkflowFactory
import node_assignment

# Once this runs right, just comment out dicts and load_node
# try loading aiida-environ, everything stored as nodes already
code = load_code(node_assignment.get("ENVIRON_CODE_PK"))
workchain = WorkflowFactory('environ.pw.adsorbate')
builder = workchain.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ adsorbate workchain"
builder.base.pw.metadata.options.resources = {'num_machines': 1}
builder.base.pw.metadata.options.max_wallclock_seconds = 30 * 60
builder.base.pw.code = code

# read in structure from ase
import ase.io
import numpy as np
a = ase.io.read("adsorbate.cif")
nat = a.get_global_number_of_atoms()
# remove the adsorbate, the cif file contains two sites that we want to take
siteA = a.pop(nat-1)
siteB = a.pop(nat-2)
structure = StructureData(ase=a)
# for idx, val in enumerate(structure.kinds):
#     print(idx, val)
# print(structure._internal_kind_tags)
# quit()
pp = get_pseudos_from_structure(structure, 'SSSPe')
vacancies = []
vacancies.append(tuple(siteA.position))
vacancies.append(tuple(siteB.position))
# set the builder
builder.structure = structure
builder.vacancies = List(list=vacancies)

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

builder.base.kpoints = load_node(node_assignment.get("SIMPLE_KPOINTS_PK"))
builder.base.pw.parameters = load_node(node_assignment.get("SIMPLE_PARAMETRES"))
builder.base.pw.pseudos = pp
builder.base.pw.environ_parameters = Dict(dict=environ_parameters)

builder.site_index = List(list=[0, 1])
builder.possible_adsorbates = List(list=['O', 'H'])
builder.adsorbate_index = List(list=[[1, 1], [1, 1]])

print(builder)
calculation = submit(builder)