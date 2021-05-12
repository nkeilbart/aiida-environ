import numpy as np
from aiida.orm import StructureData, List

def reflect_vacancies(struct_list, structure):
    def reflect_point(vec1, vec2, vecp):
        cross = np.cross(vec1, vec2)
        t = -(np.dot(cross, vecp) / np.dot(cross, cross))
        reflected_point = vecp + 2 * t * cross
        return reflected_point
    vec1 = np.array(structure.sites[1].position) - np.array(structure.sites[0].position)
    vec2 = np.array(structure.sites[2].position) - np.array(structure.sites[0].position)
    new_structs = []
    for old_struct in struct_list.sites:
        struct = StructureData(cell=old_struct.cell)
        vacancies = struct[-(len(struct)-len(structure.sites)):]
        for x in vacancies:
            ref_point = reflect_point(vec1, vec2, np.array(x.position))
            if not ref_point == x.position:
                struct.append_atom(position=x.position, symbols=x.kind_name)
        struct.store()
        new_structs.append(struct.pk)
    struct_list = new_structs
