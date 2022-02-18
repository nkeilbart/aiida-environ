# -*- coding: utf-8 -*-
import math
from collections import OrderedDict
from itertools import combinations
from typing import List as Pylist
from typing import Tuple

import numpy as np
from aiida.engine import calcfunction
from aiida.orm import List, StructureData


def gen_structures_n(size: Tuple[int, int], n: int) -> Pylist:
    """Generates a list of numpy arrays, where each array is a grid representation of the adsorbate
    distribution, 1 means that an adsorbate is present on a grid space and 0 means that the adsorbate
    is not present

    Args:
        size (Tuple[int, int]): the size of the adsorbate grid
        n (int): the number of adsorbates to fill

    Returns:
        List[np.array]: list of combinations
    """
    flat = size[0] * size[1]
    combinations_ = []
    reduced_combinations = []
    for positions in combinations(range(flat), n):
        p = [0] * flat
        for i in positions:
            p[i] = 1
        p = np.array(p).reshape(size)
        combinations_.append(p)

    itcoord_list = []
    for perm in combinations_:
        coords = perm_to_coords(perm)
        itcoords = intranslatable_coords(coords)
        symmetry = False
        for ref in itcoord_list:
            if test_symmetry(itcoords, ref):
                # don't add
                symmetry = True
                break
        if not symmetry:
            itcoord_list.append(itcoords)
            reduced_combinations.append(perm)

    return reduced_combinations


def perm_to_coords(perm: np.array) -> List:
    """Converts a numpy array that represents a single permutation into a set of coordinates for the position
    of adsorbates

    Args:
        perm (np.ndarray): permutation

    Returns:
        List: coordinates list
    """
    coords = []
    for i, val in np.ndenumerate(perm):
        if val == 1:
            coords.append(i)
    return coords


def intranslatable_coords(coords: List) -> List:
    """Converts cartesian coordinates to an intranslatable representation

    Args:
        coords (List): coordinates list

    Returns:
        List: intranslatable list
    """
    itcoords = {}
    for i, c1 in enumerate(coords):
        for j, c2 in enumerate(coords):
            if i == j:
                continue
            dx = abs(c1[0] - c2[0])
            dy = abs(c1[1] - c2[1])
            length = math.hypot(dy, dx)
            angle = math.atan2(dy, dx) / math.pi
            if length not in itcoords:
                itcoords[length] = [angle]
            else:
                itcoords[length].append(angle)

    # sort everything
    itcoords = OrderedDict(sorted(itcoords.items()))
    for k in itcoords:
        itcoords[k].sort()

    return itcoords


def rotate(angle_list: List, delta: float) -> List:
    """Rotates a list of angles (wraps around at 2 pi)

    Args:
        angle_list (List): list of angles in pi radians
        delta (float): amount to change in pi radians

    Returns:
        List: new angle list in pi radians
    """
    new_angle_list = []
    for angle in angle_list:
        new_angle = angle + delta
        if new_angle >= 2.0:
            new_angle -= 2.0
        new_angle_list.append(new_angle)
    new_angle_list.sort()
    return new_angle_list


def reflect(angle_list: List) -> List:
    """Only a single reflection is required to generate all configurations, rotate
    the intranslatable coords in an arbitrary axis

    Args:
        angle_list (List): list of angles in pi radians

    Returns:
        List: new angle list in pi radians
    """
    new_angle_list = []
    for angle in angle_list:
        new_angle = 2.0 - angle
        if new_angle == 2.0:
            new_angle = 0.0
        new_angle_list.append(new_angle)
    new_angle_list.sort()
    return new_angle_list


def test_symmetry(i1: List, i2: List) -> bool:
    """Compares two set of intranslatable coordinates by considering all their rotations/reflections

    Args:
        i1 (List): intranslatable coordinates for first configuration
        i2 (List): intranslatable coordinates for second configuration

    Returns:
        bool: True if the configurations match
    """
    for length1 in i1:
        if length1 not in i2:
            return False
        if len(i1[length1]) != len(i2[length1]):
            return False
        match = False
        temp = reflect(i2)
        if i1[length1] == i2[length1]:
            match = True
        # try all rotations
        elif i1[length1] == rotate(i2[length1], 0.5):
            match = True
        elif i1[length1] == rotate(i2[length1], 1.0):
            match = True
        elif i1[length1] == rotate(i2[length1], 1.5):
            match = True
        # try reflecting once
        elif i1[length1] == temp:
            match = True
        elif i1[length1] == rotate(temp, 0.5):
            match = True
        elif i1[length1] == rotate(temp, 1.0):
            match = True
        elif i1[length1] == rotate(temp, 1.5):
            match = True

        if not match:
            return False

    return True


@calcfunction
def adsorbate_gen_supercell(parameters, structure, vacancies):
    size = (parameters["cell_shape_x"], parameters["cell_shape_y"])
    reflect = parameters["reflect_vacancies"]
    axis = parameters["system_axis"]
    n = size[0] * size[1]
    perms = []
    # 0 case (not stored)
    temp = np.zeros(size)
    # 1 case
    temp[0][0] = 1
    perms.append(np.copy(temp))
    if n > 1:
        # n-1 case
        temp = 1 - temp
        if n > 2:
            perms.append(np.copy(temp))
        # n case
        temp[0][0] = 1
        perms.append(np.copy(temp))

    if n > 3:
        for i in range(2, n - 1):
            inner_perms = gen_structures_n(size, i)
            perms.extend(inner_perms)
    struct_perms = []
    for i, x in enumerate(perms):
        list1 = []
        for j, y in enumerate(x):
            list2 = []
            for k, z in enumerate(y):
                list2.append("H" if z == 1 else 0)
            list1.append(list2)
        struct_perms.append(list1)

    # TODO: use solution for adsorbate_multitype_gen
    struct_list = []
    added = []
    for i, ads_configuration in enumerate(struct_perms):
        added_ads = 0
        new_structure = StructureData(cell=structure.cell)
        for site in structure.sites:
            new_structure.append_atom(position=site.position, symbols=site.kind_name)
        for site_configuration, pos in zip(ads_configuration, vacancies):
            for sp in site_configuration:
                if sp != 0:
                    added_ads += 1
                    new_structure.append_atom(position=pos, symbols=sp)
                    if reflect:
                        added_ads += 1
                        rpos = list(pos)
                        # assume that the structure has symmetry around the provided axis, so
                        # take the position of the axis as the mean value
                        apos = 0.0
                        for site in structure.sites:
                            apos += site.position[axis - 1]
                        apos /= len(structure.sites)
                        rpos[axis - 1] = 2 * apos - rpos[axis - 1]
                        new_structure.append_atom(position=tuple(rpos), symbols=sp)
        new_structure.store()
        struct_list.append(new_structure.pk)
        added.append(added_ads)

    struct_list = List(list=struct_list)
    added = List(list=added)

    return {"output_structs": struct_list, "num_adsorbate": added}


@calcfunction
def gen_hydrogen():
    cell = [[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]]
    struct = StructureData(cell=cell)
    struct.append_atom(position=(0.3770, 0.0, 0.0), symbols="H")
    struct.append_atom(position=(-0.3770, 0.0, 0.0), symbols="H")
    return struct
