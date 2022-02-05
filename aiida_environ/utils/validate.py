from aiida.orm import QueryBuilder, load_group
from aiida_pseudo.groups.family.pseudo import PseudoPotentialFamily


def validate_pseudo_group(group):
    qb = QueryBuilder()
    qb.append(PseudoPotentialFamily, project="label")

    # pseudo family validation
    if group in qb.all(flat=True):
        upf = load_group(group)
    else:
        raise Exception(f"\n{group} is not in aiida-pseudo families")

    return upf
