# -*- coding: utf-8 -*-
from aiida.orm import List

from aiida_environ.calculations.adsorbate.gen_multitype import _gen_multitype


def count_species(occ_list):
    count = {}
    for occ in occ_list:
        for site in occ:
            for sp in site:
                if sp in count:
                    count[sp] += 1
                else:
                    count[sp] = 1
    return count


def test_single_simple():
    print("\ntest_single_simple")
    site_index = List(list=[0])
    possible_adsorbates = List(list=["H"])
    adsorbate_index = List(list=[[1]])
    max_list = _gen_multitype(site_index, possible_adsorbates, adsorbate_index)
    assert max_list == [[[0]], [["H"]]]


def test_single_complex():
    site_index = [0, 0, 0, 0]
    possible_adsorbates = ["H", "O"]
    adsorbate_index = [[1, 1]]
    max_list = _gen_multitype(site_index, possible_adsorbates, adsorbate_index)
    ref_count = {0: 4, "H": 4, "O": 4}
    assert count_species(max_list) == ref_count


def test_multi_simple():
    site_index = [0, 1]
    possible_adsorbates = ["H"]
    adsorbate_index = [[1], [1]]
    max_list = _gen_multitype(site_index, possible_adsorbates, adsorbate_index)
    assert len(max_list) == 4


def test_multi_complex():
    site_index = [0, 0, 1, 1, 2]
    possible_adsorbates = ["H", "OH", "O"]
    adsorbate_index = [[1, 1, 0], [1, 0, 0], [1, 1, 1]]
    max_list = _gen_multitype(site_index, possible_adsorbates, adsorbate_index)
    ref_count = {0: 23, "H": 23, "OH": 11, "O": 3}
    assert len(max_list) == 12
    assert count_species(max_list) == ref_count
