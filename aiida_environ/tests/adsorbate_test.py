import math
from graph_tool.all import *
from graph_tool.correlations import combined_corr_hist
from typing import List
from copy import deepcopy
import sys
sys.path.insert(1, '../utils') # Run from aiida-environ/tests folder
from adsorbate_graph import adsorbate_possibilities

# points_per_site = [1, 4, 1]
# adsorbate_per_site = [3, 4, 4]
points_per_site = [2, 2]
adsorbate_per_site = [2, 1]
n = len(points_per_site)
adsorbate_possibilities(points_per_site, adsorbate_per_site, 2, 'graps/hist1.svg', 'graphs/graph1.pdf')