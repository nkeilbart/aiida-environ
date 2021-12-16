import unittest
from copy import deepcopy
from aiida_environ.utils.merge import recursive_update_dict

class TestUpdateDict(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestUpdateDict, self).__init__(*args, **kwargs)
        self.d = {
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

    def test_add_inner(self):
        oldd = deepcopy(self.d)
        refd = deepcopy(self.d)
        newd = {
            0: {
                3: 2
            }
        }
        refd[0][3] = 2

        recursive_update_dict(oldd, newd)
        self.assertDictEqual(oldd, refd)

    def test_replace_inner(self):
        oldd = deepcopy(self.d)
        refd = deepcopy(self.d)
        newd = {
            0: {
                2: 1
            }
        }
        refd[0][2] = 1

        recursive_update_dict(oldd, newd)
        self.assertDictEqual(oldd, refd)

    def test_add_outer(self):
        oldd = deepcopy(self.d)
        refd = deepcopy(self.d)
        newd = {
            3: {
                2: 1
            }
        }
        refd[3] = {}
        refd[3][2] = 1

        recursive_update_dict(oldd, newd)
        self.assertDictEqual(oldd, refd)


if __name__ == '__main__':
    unittest.main()
