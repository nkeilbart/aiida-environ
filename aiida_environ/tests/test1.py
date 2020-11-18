from aiida.orm.utils import load_node, load_code
from aiida.engine import submit, run
from aiida.orm import Dict, Code
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins.factories import WorkflowFactory
# Once this runs right, just comment out dicts and load_node
# try loading aiida-environ, everything stored as nodes already
code = load_code(2608)
workchain = WorkflowFactory('environ.pw.solvation')
builder = workchain.get_builder()
builder.metadata.label = "Environ test"
builder.metadata.description = "Test of environ plugin"
builder.pw.metadata.options.resources = {'num_machines': 1}
builder.pw.metadata.options.max_wallclock_seconds = 30 * 60
builder.pw.code = code

structure = load_node(2606)
pp_water = get_pseudos_from_structure(structure, 'SSSP')
kpoints = load_node(2607)
parameters = {'SYSTEM': {
    'ecutrho': 300,
    'ecutwfc': 30
}, 'ELECTRONS': {
    'conv_thr': 5.e-9,
    'diagonalization': 'cg',
    'mixing_beta': 0.4,
    'electron_maxstep': 200
}, 'CONTROL': {
    'calculation': 'scf',
    'restart_mode': 'from_scratch',
    'tprnfor': True
}
}

environ_parameters = {                                              
  'ELECTROSTATIC': {                   
        'pbc_correction': 'parabolic',
        'pbc_dim': 0,
        'tol': 1e-11,
        'mix': 0.6,
        'tol': 1e-13               
  }                                    
}                   
builder.pw.structure = structure
builder.pw.kpoints = kpoints
builder.pw.parameters = Dict(dict=parameters)
builder.pw.pseudos = pp_water
builder.pw.environ_parameters = Dict(dict=environ_parameters)

print(builder)

calculation = submit(builder)