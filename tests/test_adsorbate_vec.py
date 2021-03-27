import unittest
import numpy as np
from aiida_environ.calculations.adsorbate_vec import reflect_point
class TestAdsVec(unittest.TestCase):
    def test_hard(self):
        # Plane of 9x - 7y - 5z = 0
        vec1 = [1,2,-1]
        vec2 = [3,1,4]
        vecp = [3,-2,4]
        ans = [87/155,-16/155,166/155]
        hat = reflect_point(vec1, vec2, vecp)
        for i in range(3):
            self.assertAlmostEqual(ans[0], hat[0])

if __name__ == '__main__':
    unittest.main()