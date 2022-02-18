# -*- coding: utf-8 -*-
def get_struct_bounds(structure, axis):
    axis -= 1
    lbound = float("inf")
    ubound = float("-inf")
    for site in structure.sites:
        position = site.position[axis]
        lbound = min(lbound, position)
        ubound = max(lbound, position)

    return (lbound, ubound)
