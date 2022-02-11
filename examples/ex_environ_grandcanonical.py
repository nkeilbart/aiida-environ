# -*- coding: utf-8 -*-
import ase.io
import numpy as np
from aiida.engine import submit
from aiida.orm import Dict, List, StructureData
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_code
from aiida_quantumespresso.utils.resources import get_default_options
from make_inputs import make_simple_kpoints

from aiida.plugins import WorkflowFactory

# Once this runs right, just comment out dicts and load_node
# try loading aiida-environ, everything stored as nodes already
code = load_code(357)
workflow = WorkflowFactory("environ.pw.grandcanonical")
builder = workflow.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw grand canonical"
builder.metadata.options = get_default_options()

unit_cell = [[3.1523, 0, 0], [-1.5761, 2.7300, 0], [0, 0, 23.1547]]
mono_structure = StructureData(cell=unit_cell)
unit_cell = np.array(unit_cell)
mono_structure.append_atom(
    position=tuple(np.array([1 / 3, 2 / 3, 1 / 2]) @ unit_cell), symbols="Mo"
)
mono_structure.append_atom(
    position=tuple(np.array([2 / 3, 1 / 3, 1 / 2 - 0.0676]) @ unit_cell), symbols="S"
)
mono_structure.append_atom(
    position=tuple(np.array([2 / 3, 1 / 3, 1 / 2 + 0.0676]) @ unit_cell), symbols="S"
)

bulk_structure = StructureData(ase=ase.io.read("MoS2_bulk.cif"))

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
        "tot_charge": -0.2,
        "input_dft": "VDW-DF2-C09",
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
        "temperature": 300,
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

calculation_parameters = {
    "charge_distance": 6.0,
    "charge_max": 0.2,
    "charge_min": -0.2,
    "charge_inc": 0.1,
    "charge_spread": 0.5,
    "system_axis": 3,
    "cell_shape_x": 1,
    "cell_shape_y": 1,
}

# TODO need to fix position, use talon /storage/scratch2/mat0330/aiida/4e/99/c6f1-44b0-481b-bd94-ee5f33801924 as ref
builder.vacancies = List(
    list=[
        tuple(
            np.array([2 / 3, 1 / 3, 1 / 2 + 0.0676]) @ unit_cell + np.array([0, 0, 1.8])
        )
    ]
)
builder.mono_structure = mono_structure
builder.bulk_structure = bulk_structure
builder.calculation_parameters = Dict(dict=calculation_parameters)
builder.base.kpoints = make_simple_kpoints()
builder.base.pw.code = code
builder.base.pw.parameters = Dict(dict=parameters)
builder.base.pw.pseudos = get_pseudos_from_structure(mono_structure, "SSSPe")
builder.base.pw.environ_parameters = Dict(dict=environ_parameters)

print(builder)
calculation = submit(builder)
