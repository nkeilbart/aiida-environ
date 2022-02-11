# -*- coding: utf-8 -*-
"""This example script sets up a standard environ calculation with charges

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
code = load_code(1958)
builder = code.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.metadata.options.resources = {
    "num_machines": 1,
    "tot_num_mpiprocs": 8,
    "num_mpiprocs_per_machine": 8,
}
builder.metadata.options.max_wallclock_seconds = 30 * 60

# STRUCTURE
StructureData = DataFactory("structure")
unit_cell = [[3.1523, 0, 0], [-1.5761, 2.7300, 0], [0, 0, 23.1547]]
structure = StructureData(cell=unit_cell)
unit_cell = np.array(unit_cell)
structure.append_atom(
    position=tuple(np.array([1 / 3, 2 / 3, 1 / 2]) @ unit_cell), symbols="Mo"
)
structure.append_atom(
    position=tuple(np.array([2 / 3, 1 / 3, 1 / 2 - 0.0676]) @ unit_cell), symbols="S"
)
structure.append_atom(
    position=tuple(np.array([2 / 3, 1 / 3, 1 / 2 + 0.0676]) @ unit_cell), symbols="S"
)

# KPOINTS
KpointsData = DataFactory("array.kpoints")
kpoints_mesh = KpointsData()
kpoints_mesh.set_kpoints_mesh([1, 1, 1])

# PARAMETERS
parameters = {
    "CONTROL": {
        "calculation": "relax",
        "forc_conv_thr": 1e-3,
    },
    "SYSTEM": {
        "ecutwfc": 45,
        "ecutrho": 360,
        "occupations": "smearing",
        "degauss": 0.02,
        "smearing": "cold",
        "tot_charge": 0.0,
        "input_dft": "vdw-df2-c09",
    },
    "ELECTRONS": {
        "electron_maxstep": 200,
        "conv_thr": 1e-6,
        "mixing_mode": "local-TF",
        "mixing_beta": 0.4,
    },
    "IONS": {
        "ion_dynamics": "bfgs",
    },
}

# ENVIRON PARAMETERS
environ_parameters = {
    "ENVIRON": {
        "verbose": 1,
        "environ_restart": False,
        "environ_thr": 10,
        "env_static_permittivity": 78.3,
        "environ_type": "water",
        "env_external_charges": 2,
        "system_dim": 2,
        "system_axis": 3,
        "solvent_temperature": 300,
    },
    "BOUNDARY": {
        "rhomax": 0.01025,
        "rhomin": 0.0013,
        "solvent_mode": "full",
        "filling_threshold": 0.7,
    },
    "ELECTROSTATIC": {
        "problem": "generalized",
        "solver": "iterative",
        "auxiliary": "full",
        "tol": 1e-14,
        "maxstep": 500,
        "pbc_correction": "parabolic",
        "pbc_dim": 2,
        "pbc_axis": 3,
    },
}

# CHARGES
EnvironChargeData = DataFactory("environ.charges")
charges = EnvironChargeData()
charges.append_charge(0.5, (0.0, 0.0, 18.1419), 0.5, 2, 3)
charges.append_charge(0.5, (0.0, 0.0, 5.0128), 0.5, 2, 3)

builder.structure = structure
builder.kpoints = kpoints_mesh
builder.parameters = Dict(dict=parameters)
builder.pseudos = get_pseudos_from_structure(builder.structure, "SSSPe")
builder.environ_parameters = Dict(dict=environ_parameters)
builder.external_charges = charges

calculation = submit(builder)
print(calculation)
