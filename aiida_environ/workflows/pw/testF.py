from aiida.engine import BaseRestartWorkChain, WorkChain
from aiida.plugins import WorkflowFactory, CalculationFactory
from aiida.orm import StructureData, Dict, List, Float, Str, load_node, load_group

from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin, recursive_merge

import random

EnvPwBaseWorkChain = WorkflowFactory('environ.pw.base')

class ForceTestWorkChain(EnvPwBaseWorkChain):
    
    # TODO default block here?

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace='base',
            namespace_options={'help': 'Inputs for the `EnvPwBaseWorkChain`.'},
            exclude=('structure')
        )
        spec.input('structure', valid_type=StructureData)
        spec.input('pseudo_group', valid_type=Str)
        spec.input('settings', valid_type=Dict)
        spec.outline(
            cls.setup,
            cls.validate_structure,
            cls.validate_settings,
            cls.run_test,
            cls.display_results,
        )

    def setup(self):

        '''Setup default structure & parameters for testing. -- in progress'''

        nat = len(self.inputs.structure.sites)  # nat for random
        wild = random.randint(1, nat)           # random index

        # get user-input test parameters and set defaults
        test_parameters = self.inputs.settings.get_dict()
        test_parameters.setdefault('diff_type', 'central')          # default central difference
        test_parameters.setdefault('diff_order', 'first')           # default first-order difference
        test_parameters.setdefault('move_atom', wild)               # default random atom moved
        test_parameters.setdefault('nsteps', 5)                     # default n = 5
        test_parameters.setdefault('step_list', [0.1, 0.0, 0.0])    # default dr = dx = 0.1

        self.inputs.settings = Dict(dict=test_parameters)

    def validate_structure(self):

        # *** STRUCTURE ***
        # 2 Si atoms - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in
        # FIXME not sure how to validate structure before base workchain excepts - don't want to load every time
        
        if self.inputs.structure is None:

            cell = [[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]]
            structure = StructureData(cell=cell)
            structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
            structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')
            self.inputs.base['structure'] = structure

        # *** PSEUDO_GROUP ***

        upfstr = self.inputs.pseudo_group # FIXME pseudo group label as input?
    
        try:
            upf = load_group(upfstr)
            self.inputs.base['pseudos'] = upf.get_pseudos(structure=self.inputs.structure)
        
        except:
            raise NameError(f'{upfstr} is not an imported pseudo family. Make sure to use aiida-pseudo plugin')

    def validate_settings(self):

        # local tuples for validation
        types = ('forward', 'backward', 'central')  # finite difference type tuple
        orders = ('first', 'second')                # finite difference order tuple
        axes = ('x', 'y', 'z')                      # axis tuple

        # local variables for validation
        steplist = self.inputs.settings['step_list']
        typestr = self.inputs.settings['diff_type']
        ordstr = self.inputs.settings['diff_order']

        if not isinstance(steplist, list): raise Exception('\nstep_list must be a list of 3 floats')
        if not isinstance(typestr, str): raise Exception("\ndiff_type must be 'forward', 'backward', or 'central'")
        if not isinstance(ordstr, str): raise Exception("\ndiff_order must be 'first' or 'second'")

        # *** STEP_TUPLE ***

        # validate list length
        if len(steplist) != 3:
            raise Exception('\nAxis tuple must have 3 elements.')

        # validate float elements
        for dh in steplist:
            if not isinstance(dh, float): raise Exception(f'\nStep list may only contain float values')

        # assign axis string for calculation descriptions
        if steplist.count(0.0) == 1:
            self.ctx.axstr = axes[steplist.index(0.0)]
        elif steplist.count(0.0) == 0:
            raise Exception('\nStep size is 0')
        else:
            self.ctx.axstr = 'r'

        # *** DIFF_TYPE ***

        if typestr in types:
            self.inputs.test_parameters.diff_type = typestr

        else: # set default for garbage input
            print(f'{typestr} is not valid. Setting to central difference interpolation')
            self.inputs.test_parameters.diff_type = 'central'

        # *** DIFF_ORDER ***
        
        if ordstr in orders:
            self.inputs.test_parameters.diff_order = ordstr
        
        else: # set default for garbage input
            print(f'{ordstr} is not valid. Setting to central finite difference')
            self.inputs.test_parameters.diff_order = 'first'

    def run_test(self):

        '''Displace an atom from initial position to compare forces. -- needs testing'''

        # local variable block
        n = self.inputs.settings['nsteps'] + 1          # initial position + n-perturbations
        steps = self.inputs.settings['step_list']       # index of axis to perturb
        atom = self.inputs.settings['move_atom']        # ith atom to move
        difftype = self.inputs.settings['diff_type']    # difference type
        
        atom -= 1 # ith atom has index i-1
        prefix = f'atom{atom}' # calculation identifier prefix

        if difftype == 'central': n *= 2 # central difference requires half-step calculations

        # test atom for n-steps
        for i in range(n):

            if difftype == 'central':
                step = sum([(dh/2) ** 2 for dh in steps]) ** 0.5 # half-step increment
            else:
                step = sum([dh ** 2 for dh in steps]) ** 0.5 # full-step increment

            if i == 0: # initial calculation

                # calculation identifiers
                self.inputs.base.pw.metadata.description = 'Initial structure | d{} = {:.2}'.format(self.ctx.axstr, i * step) # brief description
                name = f'{prefix}.{self.ctx.axis}.0' # calculation node key in context dictionary

            else: # displaced atom calculations

                # get initial calculation data
                if i == 1: # only structure changes between calculations

                    initcalc = load_node(self.ctx.calculations[name]) # load initial calculation node

                    code = initcalc.inputs.base.pw.code
                    pseudos = initcalc.inputs.base.pw.pseudos
                    kpoints = initcalc.inputs.base.pw.kpoints
                    parameters = initcalc.inputs.base.pw.environ_parameters
                    settings = initcalc.inputs.base.settings

                    cell = self.initcalc.inputs.structure.cell # initial structure unit cell
                    sites = self.initcalc.inputs.structure.sites # initial structure position tuple; AiiDA Site objects
                    edge = self.initcalc.inputs.structure.cell_lengths[atom] # max cell length

                # perturb atom
                position = sites[atom].position # initial atom position
                newposition = (0., 0., 0.) # initialize new position tuple

                for j in range(3):
                    if steps[j] != 0.0:
                        newposition[j] = position[j] + i * step
                    else:
                        newposition[j] = position[j]

                sites[atom].position = newposition # update local position tuple

                # build new calculation
                if (edge - position[0]) > 0.001: # check if atom is still in cell before calculation
    
                    # builder initialization
                    builder = EnvPwBaseWorkChain.get_builder()
                    builder.pw.code = code
                    builder.pw.pseudos = pseudos
                    builder.pw.kpoints = kpoints
                    builder.parameters = parameters
                    builder.settings = settings
                    builder.metadata.description = 'Perturbed structure | d{} = {}'.format(self.ctx.axstr, i * step)
                    
                    name = f'{prefix}.{self.ctx.axstr}.{i}'

                    # add structure to builder
                    structure = StructureData(cell=cell)

                    for j in range(len(sites)):
                        structure.append_atom(position=sites[j].position, symbols=sites[j].kind_name)
                    
                    builder.structure = structure
                    
                else:

                    raise Exception('\nNew atom position appears to be outside cell bounds. Stopping.')

            # submit calculations in parallel
            calc = self.submit(EnvPwBaseWorkChain, **self.ctx.environ_parameters)
            self.to_context(**{name: calc})

            # collect the calculation pks for this atom's test series using key convention
            self.ctx.calculations = [self.ctx[f'{prefix}.{self.ctx.axstr}.{k}'].pk for k in range(n)]

    def display_results(self): # quantitative (chart) & qualitative (plot)

        '''Compare finite difference forces against DFT forces -- needs testing'''

        diff_type = self.inputs.settings['diff_type']       # difference type string
        diff_order = self.inputs.settings['diff_order']     # difference order string
        atom = self.inputs.settings['move_atom']            # index of atom perturbed
        steps = self.inputs.settings['step_list']           # list of steps
        step = sum([dh ** 2 for dh in steps]) ** 0.5        # step size -- same for all difference types

        FiniteDiffCalculation = CalculationFactory('environ.compareF')

        calclist = self.ctx.calculations
        results = FiniteDiffCalculation(
            List(list=calclist),
            Float(step),
            Str(diff_type),
            Str(diff_order),
        )

        # calculation parameters
        print()
        print(f'atom number = {atom}')
        print(f'axis        = {self.ctx.axstr}')
        print('d{}          = {}'.format(self.ctx.axstr, step))
        #print(f'environ     = {use_environ}')
        #print(f'doublecell  = {double_cell}')

        print(results) # FIXME ADD DISPLAY FORMATTING

        # header
        #print('\ncoord    energy       force      fd     err')

        # display results
        #for i in range(len(results)):
        #
        #    coord = init_coord + dh * i
        #    print('{:5.2f} {:12.8f}{:12.8f}'.format(coord, *results[i]), end=' ')
        #
        #    if 0 < i < len(results) - 1:
        #        f, fd = compute_fd(results, i)
        #        print(f'{fd:6.3f} {abs(fd - f):2.2e}', end=' ')
        #
        #    print()

        return
