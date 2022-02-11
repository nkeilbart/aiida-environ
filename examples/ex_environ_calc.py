# -*- coding: utf-8 -*-
from aiida.engine import submit
from aiida.orm.utils import load_code, load_group
from aiida_quantumespresso.utils.resources import get_default_options
from make_inputs import (
    make_simple_environ_parameters,
    make_simple_kpoints,
    make_simple_parameters,
    make_simple_structure,
)

sssp = load_group("SSSP/1.1/PBE/efficiency")

# try loading aiida-environ, everything stored as nodes already
code = load_code(1)  # Nicholas machine
builder = code.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw calcjob"
builder.metadata.options = get_default_options()

builder.structure = make_simple_structure()
builder.kpoints = make_simple_kpoints()
builder.parameters = make_simple_parameters()
builder.pseudos = sssp.get_pseudos(structure=builder.structure)  # Nicholas machine
builder.environ_parameters = make_simple_environ_parameters()

calculation = submit(builder)
print(calculation)
