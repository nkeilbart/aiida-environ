# -*- coding: utf-8 -*-
from aiida.engine import calcfunction
from aiida.orm import List, StructureData

from aiida_environ.utils.graph import Graph
from aiida_environ.utils.occupancy import Occupancy


@calcfunction
def adsorbate_gen_multitype(
    site_index: List,
    possible_adsorbates: List,
    adsorbate_index: List,
    structure: StructureData,
    adsorbate_sites: List,
):
    """Generate structures of maximally connected adsorbate configurations

    Uses a graph to connect similar adsorbate configurations. Adjacent configurations must be equivalent
    after exactly one step where one step can be either:

    - Adding

    Args:
        site_index          (aiida.orm.List):
            array of indices that describe what type of sites exist
        possible_adsorbates (aiida.orm.List):
            array of adsorbates given by strings (assumes single atomic species)
            TODO: adsorbates should be arbitrarily defined structures
        adsorbate_index     (aiida.orm.List):
            array of values that determine how many of each adsorbate can exist on each site type
        structure           (aiida.orm.StructureData):
            the structure to append adsorbates onto
        adsorbate_sites     (aiida.orm.List):
            list of coordinates to position adsorbates

    Returns:
        aiida.orm.List: a list of PK values that refer to structures that have been stored in the aiida database
            due to this function. The structures are modified versions of the input structure with possible added
            adsorbates
    """
    # Setup based on inputs
    max_list = _gen_multitype(site_index, possible_adsorbates, adsorbate_index)

    struct_list = []
    for i, ads_configuration in enumerate(max_list):
        new_structure = StructureData(cell=structure.cell)
        for site in structure.sites:
            new_structure.append_atom(position=site.position, symbols=site.kind_name)
        for site_configuration, pos in zip(ads_configuration, adsorbate_sites):
            for sp in site_configuration:
                if sp != 0:
                    new_structure.append_atom(position=pos, symbols=sp)
        new_structure.store()
        struct_list.append(new_structure.pk)

    struct_list = List(list=struct_list)

    return struct_list


def _gen_multitype(site_index: list, possible_adsorbates: list, adsorbate_index: list):
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
    # again, here things get expensive if we take the difference each time but for these sizes it's okay
    for i, occ1 in enumerate(occ_list):
        g.add_vertex(occ1)
        for j, occ2 in enumerate(occ_list):
            if i <= j:
                continue
            if occ1 - occ2 == 1:
                g.add_edge(i, j)

    n_max = 0
    for v in g.vertices:
        n_max = max(v.connections, n_max)

    def vertices_to_labels(vertex_list):
        labels = []
        for v in vertex_list:
            labels.append(v.configuration)
        ads_max_list = []
        for x in labels:
            list1 = []
            for y in x:
                list2 = []
                for z in y:
                    if z == 0:
                        list2.append(0)
                    else:
                        list2.append(possible_adsorbates[z - 1])
                list1.append(list2)
            ads_max_list.append(list1)
        return ads_max_list

    max_list = g.get_vertices_with_connections(n_max)
    max_list = vertices_to_labels(max_list)

    return max_list
