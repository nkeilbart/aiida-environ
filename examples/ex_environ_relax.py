# -*- coding: utf-8 -*-
from aiida.engine import submit
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_code
from aiida.plugins.factories import WorkflowFactory
from aiida_quantumespresso.utils.resources import get_default_options
from make_inputs import (
    make_organic_structure,
    make_simple_environ_parameters,
    make_simple_kpoints,
    make_simple_parameters,
)

# try loading aiida-environ, everything stored as nodes already
code = load_code(109)
workchain = WorkflowFactory("environ.pw.relax")
builder = workchain.get_builder()
builder.metadata.label = "environ example"
builder.metadata.description = "environ.pw relax"
builder.metadata.options = get_default_options()

builder.structure = make_organic_structure()
builder.base.kpoints = make_simple_kpoints()
builder.base.pw.code = code
builder.base.pw.parameters = make_simple_parameters()
builder.base.pw.pseudos = get_pseudos_from_structure(builder.structure, "SSSPe")
builder.base.pw.environ_parameters = make_simple_environ_parameters()
print(builder)

calculation = submit(builder)
