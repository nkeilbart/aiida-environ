import unittest
import numpy as np
from aiida_environ.calculations.adsorbate_vec import vec_point_dist
class TestAdsVec(unittest.TestCase):
    def test_easy(self):
        # Plane of 2x - 2y + 5z + 8 = 0
        vec1 = [0,9,2]
        vec2 = [-9,0,2]
        vecp = [4,-4,3]
        self.assertEqual(11*(3**0.5)/3, vec_point_dist(vec1, vec2, vecp))

if __name__ == '__main__':
    unittest.main()