# TODO move to input, or retrieve if I decide reading this from the output actually is a good idea (in the case where
# we load old output files into a database or something...)
# environ_defaults = {
#     'environ_threshold': 0.1, # in ENVIRON, this is `environ_thr`
#     'switching_function': "SCCS", # set by `&BOUNDARY/solvent_mode`
#     'switching_parameters': [0.005, 0.0001], # `rhomax` and `rhomin`
#     'static_permittivity': 1.0,
#     'epsilon_calculation': "electronic", # set by `&BOUNDARY/solvent_mode`
#     #TODO check if this is necessary alongside switching_function, consider renaming these
#     'surface_tension': 0.0, # in dyn/cm
#     'external_pressure': 0.0, # in GPa
#     'electrostatic_problem': "poisson", # set by `&ELECTROSTATIC/problem`
#     'numerical_solver': "direct", # set by `&ELECTROSTATIC/solver`
#     'auxiliary_density': "none", # set by `&ELECTROSTATIC/auxiliary`
#     'poisson_core': "fft", # set by `&ELECTROSTATIC/core`
#     'deriv_core': "analytic", # set by `&ELECTROSTATIC/core`
# }
