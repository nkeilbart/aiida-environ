from aiida_environ.calculations.energy_differentiate import calculate_finite_differences
from aiida.orm import Str, Float

dh = Float(0.1)
diff_type = Str('forward')
diff_order = Str('first')

calculate_finite_differences(dh, diff_type, diff_order)