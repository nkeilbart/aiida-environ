import sys
import unittest

# to avoid pip installing the module, add relative path
sys.path.insert(1, '../calculations')
from adsorbate_calc import AdsorbateCalculation

class TestAdsorbate(unittest.TestCase):
    def test_simple(self):
        site_index = [0, 0]
        possible_adsorbates = ['H']
        adsorbate_index = [[1]]
        max_list = AdsorbateCalculation(site_index, possible_adsorbates, adsorbate_index)
        print(max_list)

if __name__ == '__main__':
    unittest.main()
