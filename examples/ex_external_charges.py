# -*- coding: utf-8 -*-
from aiida.engine import run
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_code
from aiida.plugins.factories import DataFactory
from aiida_quantumespresso.utils.resources import get_default_options
from make_inputs import (
    make_organic_structure,
    make_simple_environ_parameters,
    make_simple_kpoints,
    make_simple_parameters,
)

# try loading aiida-environ, everything stored as nodes already
code = load_code()
builder = code.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw external charges"
builder.metadata.options = get_default_options()

# this makes no sense but we'll create a dry run and check the environ.in file
EnvironChargeData = DataFactory("environ.charges")
charges = EnvironChargeData()
charges.append_charge(1, (0, 0, 0), 1.0, 0, 1)

builder.structure = make_organic_structure()
builder.kpoints = make_simple_kpoints()
builder.parameters = make_simple_parameters()
builder.pseudos = get_pseudos_from_structure(builder.structure, "SSSPe")
builder.environ_parameters = make_simple_environ_parameters()
builder.external_charges = charges

calculation = run(builder)
