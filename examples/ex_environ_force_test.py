# -*- coding: utf-8 -*-
from aiida.engine import submit
from aiida.orm import Dict, Str
from aiida.orm.utils import load_code, load_group
from aiida_quantumespresso.utils.resources import get_default_options
from make_inputs import (
    make_simple_environ_parameters,
    make_simple_kpoints,
    make_simple_parameters,
    make_simple_structure,
)

from aiida.plugins import WorkflowFactory


code = load_code(1)
workchain = WorkflowFactory("environ.pw.force_test")
builder = workchain.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw force workchain"
builder.structure = make_simple_structure()

builder.test_settings = Dict(
    dict={
        "diff_type": "central",
        "diff_order": "second",
        "atom_to_perturb": 2,
        "n_steps": 5,
        "step_sizes": [0.01, 0.00, 0.01],
    }
)

sssp = load_group("SSSP/1.1/PBE/efficiency")

builder.base.pw.code = code
builder.base.pw.parameters = make_simple_parameters()
builder.base.pw.pseudos = sssp.get_pseudos(structure=builder.structure)
builder.base.pw.environ_parameters = make_simple_environ_parameters()
builder.base.pw.metadata.options = get_default_options(with_mpi=True)
builder.base.kpoints = make_simple_kpoints()

print(builder)
calculation = submit(builder)
