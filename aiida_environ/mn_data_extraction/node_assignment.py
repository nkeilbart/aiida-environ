import json

from aiida.plugins.factories import DataFactory
import aiida
aiida.load_profile('ajay')
def get(pk):
    d = {}
    with open("pk_vals.json", 'r') as f:
        d = json.load(f)
    try:
        return d[pk]
    except KeyError:
        return None

def make_simple_structure() -> int:
    StructureData = DataFactory('structure')
    unit_cell = [[10.5835431576, 0, 0], [0, 10.5835431576, 0], [0, 0, 10.5835431576]]

    structure = StructureData(cell=unit_cell)
    structure.append_atom(position=(6.2629149502, 6.3834874485, 6.08553686585), symbols="O")
    structure.append_atom(position=(7.1075976684, 5.8856629291, 6.08553686585), symbols="H")
    structure.append_atom(position=(5.5740299405, 5.6858323849, 6.08553686585), symbols="H")
    structure.store()

    return structure.pk

def make_simple_kpoints() -> int:
    KpointsData = DataFactory('array.kpoints')
    kpoints_mesh = KpointsData()
    kpoints_mesh.set_kpoints_mesh([1, 1, 1])
    kpoints_mesh.store()

    return kpoints_mesh.pk

def make_organic_structure() -> int:
    import ase.io
    a = ase.io.read("NEUTRAL_017.in")
    StructureData = DataFactory('structure')
    structure = StructureData(ase=a)
    structure.label = "240 small neutral organic molecule set, id: 17"
    structure.store()

    return structure.pk

def make_simple_parameters() -> int:
    from aiida.orm import Dict
    parameters = {
        "CONTROL": {
            "calculation": "scf",
            "restart_mode": "from_scratch",
            "tprnfor": True
        },
        'SYSTEM': {
            'ecutrho': 300,
            'ecutwfc': 30
        }, 
        'ELECTRONS': {
            'conv_thr': 5.e-9,
            'diagonalization': 'cg',
            'mixing_beta': 0.4,
            'electron_maxstep': 200
        }
    }
    parameters = Dict(dict=parameters)
    parameters.store(parameters)

    return parameters.pk
    
if __name__ == '__main__':
    from os import path
    pk_file = "pk_vals.json"
    simple_structure_pk = make_simple_structure()
    simple_kpoints_pk = make_simple_kpoints()
    simple_parameters_pk = make_simple_parameters()
    organic_structure_pk = make_organic_structure()

    d = {}
    if path.exists(pk_file):
        with open(pk_file, 'r') as f:
            d = json.load(f)

    d["SIMPLE_STRUCTURE_PK"] = simple_structure_pk
    d["SIMPLE_KPOINTS_PK"] = simple_kpoints_pk
    d["SIMPLE_PARAMETERS_PK"] = simple_parameters_pk
    d["ORGANIC_STRUCTURE_PK"] = organic_structure_pk

    with open(pk_file, 'w') as f:
        json_obj = json.dumps(d, indent=4)
        f.write(json_obj)