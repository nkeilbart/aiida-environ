import math
from graph_tool.all import *
from graph_tool.correlations import combined_corr_hist
from typing import List
from copy import deepcopy
import matplotlib.pyplot as plt
from aiida.engine import calcfunction
import sys
sys.path.insert(1, '../utils') # Run from aiida-environ/tests folder
import json
from occupancy import Occupancy
import numpy as np

# @calcfunction
def adsorbate_calculation(site_index, possible_adsorbates, adsorbate_index):
    # Setup based on inputs
    points_per_site = [0] * (max(site_index) + 1)
    adsorbate_per_site = [0] * (max(site_index) + 1)
    for i in site_index:
        points_per_site[i] += 1
    for i, site in enumerate(adsorbate_index):
        adsorbate_per_site[i] = sum(site)
    assert len(points_per_site) == len(adsorbate_per_site)  
    o = Occupancy(points_per_site, adsorbate_per_site)
    g = Graph()
    # note that the current implementation clones the configuration list (deepcopy) which may get expensive but for our purposes should be fine
    occ_list = list(o)
    vertices = list(g.add_vertex(len(occ_list)))
    v_prop = g.new_vertex_property("string")
    # again, here things get expensive if we take the difference each time but for these sizes it's okay
    n_max = 0
    for i, occ1 in enumerate(occ_list):
        n = 0
        v_prop[vertices[i]] = occ1.configuration
        for j, occ2 in enumerate(occ_list):
            if i >= j:
                continue
            if occ1 - occ2 == 1:
                g.add_edge(vertices[i], vertices[j])
                g.add_edge(vertices[j], vertices[i])
                n += 1
        n_max = max(n_max, n)

    def get_vertices_with_degree(vertex_list, n):
        out = []
        for v in vertex_list:
            if v.in_degree() == n:
                out.append(v)
        return out  

    def vertices_to_labels(vertex_list, prop):
        labels = []
        for v in vertex_list:
            labels.append(json.loads(prop[v]))
        ads_max_list = []
        for i, x in enumerate(labels):
            list1 = []
            for j, y in enumerate(x):
                list2 = []
                for k, z in enumerate(y):
                    if (z == 0):
                        list2.append(0)
                    else:
                        list2.append(possible_adsorbates[z - 1])
                list1.append(list2)
            ads_max_list.append(list1)
        return ads_max_list

    max_list = get_vertices_with_degree(vertices, n_max)
    max_list = vertices_to_labels(max_list, v_prop) 
    
    return max_list
