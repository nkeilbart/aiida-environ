import math
from graph_tool.all import *
from graph_tool.correlations import combined_corr_hist
from typing import List
from copy import deepcopy
import matplotlib.pyplot as plt

# points_per_site = [1, 4, 1]
# adsorbate_per_site = [3, 4, 4]
points_per_site = [2, 2]
adsorbate_per_site = [2, 1]
n = len(points_per_site)

def combination_with_repitition(n: int, r: int) -> int:
    """In this context, computes the possible combinations of adsorbates on a single type of site

    Args:
        n (int): number of points per site
        r (int): number of types of adsorbate on site

    Returns:
        int: combinations
    """
    a = math.factorial(n + r - 1)
    b = math.factorial(r)
    c = math.factorial(n - 1)
    return a / (b * c)

class Occupancy:
    def __init__(self, pps: List, aps: List):
        assert len(pps) == len(aps)
        n = len(pps)
        self.pps = pps
        self.aps = aps
        self.configuration = []
        for i in range(n):
            inner_configuration = [0] * pps[i]
            self.configuration.append(inner_configuration)
        # hack to enforce initial iterable
        self.configuration[-1][-1] = -1
        
    def __str__(self):
        return self.configuration.__str__()

    def __repr__(self):
        return self.configuration.__repr__()
    
    def __iter__(self):
        return self

    def clone(self):
        clone = Occupancy(self.pps, self.aps)
        clone.configuration = deepcopy(self.configuration)
        return clone

    def next_inner(self, inner, index):
        result = deepcopy(inner)
        i = len(result) - 1
        while True:
            result[i] += 1
            if result[i] <= self.aps[index]:
                if i < len(result) - 1:
                    j = i + 1
                    while j < len(result):
                        result[j] = result[i]
                        j += 1
                return result
            else:
                result[i] = 0
                i -= 1
                if i < 0:
                    return None
    
    def __next__(self):
        i = len(self.configuration)
        while True:
            i -= 1
            if i < 0:
                raise StopIteration
            temp = self.next_inner(self.configuration[i], i)
            if temp is not None:
                self.configuration[i] = temp
                return self.clone()
            else:
                self.configuration[i] = [0] * self.pps[i]

    def __sub__(self, other):
        assert self.pps == other.pps
        assert self.aps == other.aps
        diff = 0
        n = len(self.pps)
        #print(self.configuration, other.configuration)
        for i in range(n):
            temp = deepcopy(other.configuration)
            for j, val in enumerate(self.configuration[i]):
                if val in temp[i]:
                    temp[i][temp[i].index(val)] = -1
                else:
                    diff += 1
            # for j in range(self.pps[i]):
            #     cdiff = int((self.configuration[i][j] - other.configuration[i][j]) != 0)
            #     #print(cdiff, end=' ')
            #     diff += cdiff
        #print("diff:", diff)
        return diff



def adsorbate_possibilities(points_per_site, adsorbate_per_site, max_list_nodes, out_hist, out_graph):
    # combinations = 1
    # for i in range(n):
    #     combinations *= combination_with_repitition(points_per_site[i], adsorbate_per_site[i])
    assert len(points_per_site) == len(adsorbate_per_site)  
    o = Occupancy(points_per_site, adsorbate_per_site)
    g = Graph()
    # note that the current implementation clones the configuration list (deepcopy) which may get expensive but for our purposes should be fine
    occ_list = list(o)
    # print('Length:', len(occ_list))
    # print(occ_list)
    vertices = list(g.add_vertex(len(occ_list)))
    v_prop = g.new_vertex_property("string")
    # again, here things get expensive if we take the difference each time but for these sizes it's okay
    for i, occ1 in enumerate(occ_list):
        v_prop[vertices[i]] = occ1.__str__()
        for j, occ2 in enumerate(occ_list):
            if i >= j:
                continue
            if occ1 - occ2 == 1:
                g.add_edge(vertices[i], vertices[j])
                g.add_edge(vertices[j], vertices[i])

    def get_vertices_with_degree(vertices, n):
        out = []
        for v in vertices:
            if v.in_degree() == n:
                out.append(v)
        return out  

    # max_list = get_vertices_with_degree(vertices, max_list_nodes)
    # print(len(max_list))
    # for l in max_list:
    #     print("VERTEX")
    #     print(v_prop[l])
    #     print("NEIGHBOURS")
    #     for v in l.in_neighbours():
    #         print(v_prop[v])
                
    hist = combined_corr_hist(g, "in", "out")
    plt.figure()
    plt.imshow(hist[0].T, interpolation="nearest", origin="lower")
    plt.colorbar()
    plt.xlabel("in-degree")
    plt.ylabel("out-degree")
    plt.tight_layout()
    plt.savefig(out_hist)


    pos = sfdp_layout(g)
    graph_draw(g, pos, output=out_graph, ink_scale=0.2, output_size=(1000, 1000))
