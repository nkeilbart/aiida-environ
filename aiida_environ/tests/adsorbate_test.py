import math
from graph_tool.all import *
from graph_tool.correlations import combined_corr_hist
from typing import List
from copy import deepcopy
import sys
import os
sys.path.insert(1, '../calculations') # Run from aiida-environ/tests folder
from adsorbate_calc import AdsorbateCalculation

site_index = [0, 0, 1, 1, 2]
possible_adsorbates = ['H', 'HO', 'O', 'Cl']
adsorbate_index = [[1, 1, 0, 0], [1, 1, 1, 1], [1, 1, 1, 1]]
max_list = AdsorbateCalculation(site_index, possible_adsorbates, adsorbate_index)
print(max_list)
