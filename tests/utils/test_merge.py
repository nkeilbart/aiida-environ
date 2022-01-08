import pytest

from copy import deepcopy
from aiida_environ.utils.merge import recursive_update_dict


def get_test_dict() -> dict:
    d = {
        0: {
            0: 2,
            1: 4,
            2: 3
        }, 
        1: {
            0: 3,
            1: 5,
            2: 1
        }
    }
    return d


def test_add_inner():
    d = get_test_dict()
    oldd = deepcopy(d)
    refd = deepcopy(d)
    newd = {
        0: {
            3: 2
        }
    }
    refd[0][3] = 2

    recursive_update_dict(oldd, newd)
    assert oldd == refd


def test_replace_inner():
    d = get_test_dict()
    oldd = deepcopy(d)
    refd = deepcopy(d)
    newd = {
        0: {
            2: 1
        }
    }
    refd[0][2] = 1

    recursive_update_dict(oldd, newd)
    assert oldd == refd


def test_add_outer():
    d = get_test_dict()
    oldd = deepcopy(d)
    refd = deepcopy(d)
    newd = {
        3: {
            2: 1
        }
    }
    refd[3] = {}
    refd[3][2] = 1

    recursive_update_dict(oldd, newd)
    assert oldd == refd
