import unittest
from aiida_environ.calculations.adsorbate_calc import adsorbate_calculation

class TestAdsorbate(unittest.TestCase):
    def count_species(self, occ_list):
        count = {}
        for occ in occ_list:
            for site in occ:
                for sp in site:
                    if sp in count:
                        count[sp] += 1
                    else:
                        count[sp] = 1
        return count

    def test_single_simple(self):
        site_index = [0, 0]
        possible_adsorbates = ['H']
        adsorbate_index = [[1]]
        max_list = adsorbate_calculation(site_index, possible_adsorbates, adsorbate_index)
        self.assertEqual(max_list, [[[0, 'H']]])
        
    def test_single_complex(self):
        site_index = [0, 0, 0, 0]
        possible_adsorbates = ['H', 'O']
        adsorbate_index = [[1, 1]]
        max_list = adsorbate_calculation(site_index, possible_adsorbates, adsorbate_index)
        ref_count = {
            0: 4,
            'H': 4,
            'O': 4
        }
        self.assertDictEqual(self.count_species(max_list), ref_count)

    def test_multi_simple(self):
        site_index = [0, 1]
        possible_adsorbates = ['H']
        adsorbate_index = [[1], [1]]
        max_list = adsorbate_calculation(site_index, possible_adsorbates, adsorbate_index)
        self.assertEqual(len(max_list), 4)
    
    def test_multi_complex(self):
        site_index = [0, 0, 1, 1, 2]
        possible_adsorbates = ['H', 'OH', 'O']
        adsorbate_index = [[1, 1, 0], [1, 0, 0], [1, 1, 1]]
        max_list = adsorbate_calculation(site_index, possible_adsorbates, adsorbate_index)
        print(max_list)
        print(self.count_species(max_list))


if __name__ == '__main__':
    unittest.main()
