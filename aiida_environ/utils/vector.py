import numpy as np
from aiida.orm import StructureData

def reflect_vacancies(struct_list, structure, axis):
    # NOTE: for now, just take in an axis, since multilayer slabs are possible
    # and we should rely on a principal direction for now. Maybe fix this automation
    # in the future...

    # def reflect_point(vec1, vec2, vecp):
    #     cross = np.cross(vec1, vec2)
    #     t = -(np.dot(cross, vecp) / np.dot(cross, cross))
    #     reflected_point = vecp + 2 * t * cross
    #     return reflected_point

    def reflect_point(position, axis):
        if axis == 1:
            vec = np.array([1, 0, 0])
        elif axis == 2:
            vec = np.array([0, 1, 0])
        elif axis == 3:
            vec = np.array([0, 0, 1])
        else:
            raise ValueError("axis value 1-3 expected")
        t = -(np.dot(vec, position) / np.dot(vec, vec))
        reflected = position + 2 * t * vec

    new_structs = []
    for old_struct in struct_list.sites:
        struct = StructureData(cell=old_struct.cell)
        vacancies = struct[-(len(struct)-len(structure.sites)):]
        for x in vacancies:
            ref_point = reflect_point(np.array(x.position), axis)
            if not ref_point == x.position:
                struct.append_atom(position=x.position, symbols=x.kind_name)
        struct.store()
        new_structs.append(struct.pk)
    struct_list = new_structs

def get_struct_bounds(structure, axis):
    axis -= 1
    lbound = float("inf")
    ubound = float("-inf")
    for site in structure.sites:
        position = site.position[axis]
        lbound = min(lbound, position)
        ubound = max(lbound, position)
    
    return (lbound, ubound)


