# -*- coding: utf-8 -*-
import ase.io
from aiida.engine import submit
from aiida.orm import Dict, List, StructureData
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_code
from aiida.plugins.factories import WorkflowFactory
from aiida_quantumespresso.utils.resources import get_default_options
from make_inputs import make_simple_kpoints, make_simple_parameters

# Once this runs right, just comment out dicts and load_node
# try loading aiida-environ, everything stored as nodes already
code = load_code()
workchain = WorkflowFactory("environ.pw.graphml")
builder = workchain.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw graph ml"
builder.metadata.options = get_default_options()

a = ase.io.read("adsorbate.cif")
nat = a.get_global_number_of_atoms()
# remove the adsorbate, the cif file contains two sites that we want to take
siteA = a.pop(nat - 1)
siteB = a.pop(nat - 2)
structure = StructureData(ase=a)

adsorbate_sites = []
adsorbate_sites.append(tuple(siteA.position))
adsorbate_sites.append(tuple(siteB.position))
# set the builder
builder.structure = structure
builder.adsorbate_sites = List(list=adsorbate_sites)

environ_parameters = {
    "ENVIRON": {
        "environ_restart": False,
        "env_electrostatic": True,
        "environ_thr": 0.1,
    },
    "BOUNDARY": {"alpha": 1.12, "radius_mode": "muff", "solvent_mode": "ionic"},
    "ELECTROSTATIC": {"tol": 1e-10},
}

builder.base.kpoints = make_simple_kpoints()
builder.base.pw.code = code
builder.base.pw.parameters = make_simple_parameters()
builder.base.pw.pseudos = get_pseudos_from_structure(structure, "SSSPe")
builder.base.pw.environ_parameters = Dict(dict=environ_parameters)

builder.site_index = List(list=[0, 1])
builder.possible_adsorbates = List(list=["O", "H"])
builder.adsorbate_index = List(list=[[1, 1], [1, 1]])

print(builder)
calculation = submit(builder)
