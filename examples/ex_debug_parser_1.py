# -*- coding: utf-8 -*-
"""This example script sets up a standard environ calculation with an electrolyte

Functionality for the debug parser can be seen here (activated by verbose=1 in 
the `environ_parameters["ENVIRON"]` dictionary)
"""

import numpy as np
from aiida.engine import submit
from aiida.orm import Dict
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_code
from aiida.plugins.factories import DataFactory

# USER SHOULD CHANGE FOR THEIR SYSTEM
code = load_code(109)
builder = code.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.metadata.options.resources = {
    "num_machines": 1,
    "tot_num_mpiprocs": 4,
    "num_mpiprocs_per_machine": 4,
}
builder.metadata.options.max_wallclock_seconds = 30 * 60

# STRUCTURE
StructureData = DataFactory("structure")
unit_cell = [[2.9335, 0, 0], [0, 2.9335, 0], [0, 0, 34.4418]]
structure = StructureData(cell=unit_cell)
unit_cell = np.array(unit_cell)
structure.append_atom(position=(1.46675, 1.46675, 10.000), symbols="Ag")
structure.append_atom(position=(0.00000, 0.00000, 12.033669694), symbols="Ag")

# KPOINTS
KpointsData = DataFactory("array.kpoints")
kpoints_mesh = KpointsData()
kpoints_mesh.set_kpoints_mesh([1, 1, 1])

parameters = {
    "CONTROL": {
        "calculation": "scf",
        "tprnfor": True,
    },
    "SYSTEM": {
        "nspin": 1,
        "ecutwfc": 35,
        "ecutrho": 350,
        "occupations": "smearing",
        "degauss": 0.01,
        "smearing": "marzari-vanderbilt",
        "tot_charge": 0.0,
    },
    "ELECTRONS": {
        "mixing_beta": 0.3,
        "conv_thr": 1e-6,
    },
}

# ENVIRON PARAMETERS
environ_parameters = {
    "ENVIRON": {
        "verbose": 1,
        "environ_thr": 10,
        "system_dim": 2,
        "system_axis": 3,
        "env_static_permittivity": 80,
        "env_electrolyte_ntyp": 2,
        "electrolyte_linearized": False,
        "temperature": 300,
        "zion(1)": 1,
        "cion(1)": 0.01,
        "zion(2)": -1,
        "cion(2)": 0.01,
    },
    "BOUNDARY": {
        "electrolyte_spread": 0.001,
        "electrolyte_distance": 20.2137,
        "electrolyte_mode": "system",
    },
    "ELECTROSTATIC": {
        "solver": "iterative",
        "auxiliary": "full",
        "pbc_correction": "gcs",
        "pbc_dim": 2,
        "pbc_axis": 3,
        "tol": 1e-11,
    },
}

builder.structure = structure
builder.kpoints = kpoints_mesh
builder.parameters = Dict(dict=parameters)
builder.pseudos = get_pseudos_from_structure(builder.structure, "SSSPe")
builder.environ_parameters = Dict(dict=environ_parameters)

calculation = submit(builder)
print(calculation)
