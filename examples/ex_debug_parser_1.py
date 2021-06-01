from aiida import load_profile
load_profile()

from aiida.orm import Dict
from aiida.orm.utils import load_code
from aiida.engine import submit
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import DataFactory
import numpy as np

# try loading aiida-environ, everything stored as nodes already
code = load_code(109)
builder = code.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.metadata.options.resources = {
        'num_machines': 1,
        'tot_num_mpiprocs': 4,
        'num_mpiprocs_per_machine': 4
}
builder.metadata.options.max_wallclock_seconds = 30 * 60

StructureData = DataFactory('structure')
unit_cell = [[2.9335, 0, 0], [0, 2.9335, 0], [0, 0, 34.4418]]
structure = StructureData(cell=unit_cell)
unit_cell = np.array(unit_cell)
structure.append_atom(position=(1.46675, 1.46675, 10.000), symbols="Ag")
structure.append_atom(position=(0.00000, 0.00000, 12.033669694), symbols="Ag")

KpointsData = DataFactory('array.kpoints')
kpoints_mesh = KpointsData()
kpoints_mesh.set_kpoints_mesh([18, 18, 1])

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
    }
}

builder.structure = structure
builder.kpoints = kpoints_mesh
builder.parameters = Dict(dict=parameters)
builder.pseudos = get_pseudos_from_structure(builder.structure, 'SSSPe')
builder.environ_parameters = Dict(dict=environ_parameters)

calculation = submit(builder)
print(calculation)
