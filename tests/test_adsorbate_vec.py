import unittest
import numpy as np
from aiida_environ.calculations.adsorbate_vec import reflect_point
from aiida_environ.calculations.adsorbate_vec import point_project
class TestAdsVec(unittest.TestCase):
    def test_reflect(self):
        # Plane of 9x - 7y - 5z = 0
        vec1 = [1,2,-1]
        vec2 = [3,1,4]
        vecp = [3,-2,4]
        ans = [87/155,-16/155,166/31]
        hat = reflect_point(vec1, vec2, vecp)
        for i in range(3):
            self.assertAlmostEqual(ans[i], hat[i])

if __name__ == '__main__':
    unittest.main()