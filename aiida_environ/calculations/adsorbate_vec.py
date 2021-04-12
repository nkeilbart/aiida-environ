import numpy as np
from aiida.orm import StructureData, List

def reflect_vacancies(structure, vacancies):
    def reflect_point(vec1, vec2, vecp):
        cross = np.cross(vec1, vec2)
        t = -(np.dot(cross, vecp) / np.dot(cross, cross))
        reflected_point = vecp + 2 * t * cross
        return reflected_point

    vec1 = np.array(structure.sites[1].position) - np.array(structure.sites[0].position)
    vec2 = np.array(structure.sites[2].position) - np.array(structure.sites[0].position)
    reflected = vacancies
    for x in vacancies:
        ref_point = reflect_point(vec1, vec2, np.array(x))
        if not ref_point == x:
            reflected.append(ref_point)
    reflected = List(list=reflected)
    return reflected
