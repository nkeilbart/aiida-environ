from aiida.orm import QueryBuilder, Dict, Group, StructureData
from aiida.orm.utils import load_node
import numpy as np
import pdb

def solvent_pk(label):
    qb = QueryBuilder()
    qb.append(Group, filters={'label': {'==': 'solvent group'}}, tag='solvents')
    qb.append(Dict, filters={'label': {'==': label}}, with_group='solvents', project=['id', 'attributes.eps'])
    # qb.append(Dict, with_group='solvents', project=['label'])
    qb.limit(None)
    return qb.all()[-1][0] # Holds PK and eps val but only returns PK

def solvent_structs(label, lim=None):
    qb = QueryBuilder()
    qb.append(Group, filters={'label': {'==': 'solute group'}}, tag='solutes')
    pk = solvent_pk(label)
    qb.append(Dict, filters={'attributes.solvent': {'==': pk}}, with_group='solutes')#, project=['attributes.solute'])
    # pks = [item for sublist in qb.all() for item in sublist]
    # qb2 = QueryBuilder()
    # qb2.append(StructureData, filters={'id': {'in': pks}})
    # return list(np.array(qb2.all()).flatten())
    if lim is not None:
        qb.limit(lim)
    return list(np.array(qb.all()).flatten())

def struct_and_dict(dicts):
    structs = []
    for d in dicts:
        # struct = load_node(d.attributes.solute)
        struct = load_node(d['solute'])
        structs.append(struct)
    return structs, dicts

for d in solvent_structs('octanol', 10):
    print(d.attributes['solute'])