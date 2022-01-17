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
            exclude=('pw.structure')
        )
        spec.input('test_parameters', valid_type=Dict)
        spec.outline(
            cls.setup,
            cls.validate_settings,
            cls.run_test,
            cls.display_results,
        )

    def validate_settings(self):

        # local tuples for validation
        difftypes = ('forward', 'backward', 'central')           # finite difference type tuple
        difforders = ('first', 'second')                         # finite difference order tuple
        axes = ('x', 'y', 'z')                                   # axis tuple

        # local variables for validation
        stepinput = self.inputs.test_parameters.step             # step size input
        axinput = self.inputs.test_parameters.axis               # axis input
        multi = self.inputs.test_paramaters.multivar             # multi flag

        # *** VALIDATE MULTI ***

        if multi: # change atom position in more than one variable (r + dr)
            
            axinput: list[str]
            stepinput: list[float]

            if len(axinput) < 1 or len(axinput) > 3:
                raise Exception('\nAxis list length not valid not valid.')
            for ax in axinput:
                if ax not in axes:
                    raise Exception(f'\nAxis string {ax} not valid. Setting to x & y')
            if len(stepinput) != len(axinput):
                raise Exception('\nStep list length must be same length as axis list.')
            
            dr = sum(dh ** 2 for dh in stepinput) ** 0.5

            self.inputs.test_parameters.step = dr
            self.ctx.axstr = 'r'
            
        else:

            axinput: str
            stepinput: float

            if axinput in axes:
                self.inputs.test_parameters.axis = axes.index(axinput)
            else: # set default for garbage input
                print('\nAxis selection not valid. Setting to random axis')
                self.inputs.test_parameters.axis = wild # FIXME pass to method or assign to context
        
            self.ctx.axstr = axinput # useful for calc descriptions

        # *** VALIDATE DIFF_TYPE ***

        typestr = self.inputs.test_parameters.diff_type
        
        if typestr in difftypes:
            self.inputs.test_parameters.diff_type = typestr

        else: # set default for garbage input
            print(f'{typestr} is not valid. Setting to central difference interpolation')
            self.inputs.test_parameters.diff_type = 'central'

        # *** VALIDATE ORDER ***

        ordstr = self.inputs.test_parameters.diff_order
        
        if ordstr in difforders:
            self.inputs.test_parameters.diff_order = ordstr
        
        else: # set default for garbage input
            print(f'{ordstr} is not valid. Setting to central finite difference')
            self.inputs.test_parameters.diff_order = 'first'

    def setup(self):

        '''Setup default structure & parameters for testing. -- in progress'''
        
        # validate structure
        # 2 Si atoms - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in
        # FIXME not sure how to validate structure before base workchain excepts - don't want to load every time
        
        if self.inputs.base['structure'] is None:

            cell = [[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]]
            structure = StructureData(cell=cell)
            structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
            structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')
            self.inputs.base['structure'] = structure

        # validate pseudo string

        if self.inputs.base.pw['pseudos'] is None:

            upfstr = self.inputs.test_parameters.pseudo # FIXME pseudo group label as input?
            upfstr = '' # FIXME FOR TESTING ONLY
        
            try:
                upf = load_group(upfstr)
                self.inputs.base['pseudos'] = upf.get_pseudos(structure=self.inputs.base.pw['structure'])
            
            except:
                raise NameError(f'{upfstr} is not an imported pseudo family. Make sure to use aiida-pseudo plugin')

        nat = self.inputs.base.pw.parameters['CONTROL']['nat']   # nat for random
        wild = random.randint(1, nat)                            # random index

        # get user-input test parameters and set defaults
        chain_parameters = self.inputs.test_parameters.get_dict()
        chain_parameters.setdefault('diff_type', 'central')       # default central difference
        chain_parameters.setdefault('diff_order', 'first')        # default first-order difference
        chain_parameters.setdefault('multivar', False)            # default single-variable difference
        chain_parameters.setdefault('move_atom', 1)               # default first atom moved
        chain_parameters.setdefault('nsteps', 5)                  # default n = 5
        chain_parameters.setdefault('axis', wild)                 # default random direction (int)
        chain_parameters.setdefault('step', 0.1)                  # default dx = 0.1   

        self.inputs.test_parameters = Dict(dict=chain_parameters)

    def run_test(self):

        '''Displace an atom from initial position to compare forces. -- needs testing'''

        # test parameter variable block for logic legibility
        atom = self.inputs.test_parameters.move_atom            # ith atom to move
        axis = self.inputs.test_parameters.axis                 # index of axis to perturb
        dtype = self.inputs.test_parameters.diff_type           # difference type
        
        atom -= 1 # ith atom has index i-1
        prefix = f'atom{atom}'

        if dtype == 'central':
            n = 2 * (self.inputs.test_parameters.nsteps + 1) # 2n steps needed for half & whole steps
        else:
            n = self.inputs.test_parameters.nsteps + 1

        # test atom for n-steps
        for i in range(n):

            if dtype == 'central':
                step = self.inputs.test_parameters.step / 2
            else:
                step = self.inputs.test_parameters.step

            if i == 0: # initial calculation

                # calculation identifiers
                self.inputs.pw.metadata.description = 'Initial structure | d{} = {:.2}'.format(self.ctx.axstr, i * step) # brief description
                name = f'{prefix}.{axis}.0' # calculation node key in context dictionary

            else: # displaced atom calculations

                # get initial calculation data
                if i == 1: # only structure changes between calculations

                    initname = f'{prefix}.{self.ctx.axstr}.0' # assign initial calculation name
                    initcalc = load_node(self.ctx.calculations[initname]) # load initial calculation node

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
                newposition = (0., 0., 0.)
                for j in range(len(position)): # build new position tuple
                    if j == axis:
                        newposition[axis] = position[axis] + i * step
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
                    builder.metadata.description = 'Perturbed structure | {}'.format(i * step)
                    
                    name = f'{prefix}.{self.ctx.axstr}.{i * step}'

                    # add structure to builder
                    structure = StructureData(cell=cell)
                    for j in range(len(sites)):
                        structure.append_atom(position=sites[j].position, symbols=sites[j].kind_name)
                    builder.structure = structure
                    
                else:

                    print('\nNew atom position appears to be outside cell bounds. Stopping.')
                    quit()

            # submit calculations in parallel
            calc = self.submit(EnvPwBaseWorkChain, **self.ctx.environ_parameters)
            self.to_context(**{name: calc})

            # collect the calculation pks for this atom's test series using key convention
            self.ctx.calculations = [self.ctx[f'{prefix}.{self.ctx.axstr}.{k*step}'].pk for k in range(n)]

    def display_results(self): # quantitative (chart) & qualitative (plot)

        '''Compare finite difference forces against DFT forces -- needs testing'''

        diff_type = self.inputs.test_parameters.diff_type       # difference type string
        diff_order = self.inputs.test_parameters.diff_order     # difference order string
        atoms = self.inputs.test_parameters.move_list           # index of atom perturbed
        step = self.inputs.test_parameters.step                 # step size float

        CompareCalculation = CalculationFactory('environ.compareF')

        results = {}
        for atom in atoms:

            calclist = self.ctx.calculations
            results[atom] = CompareCalculation(
                List(list=calclist),
                Str(diff_type),
                Str(diff_order),
                Float(step)
            )

            # calculation parameters
            print()
            print(f'atom number = {atom}')
            print(f'axis        = {self.ctx.axstr}')
            print(f'd{self.ctx.axstr}          = {step}')
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
