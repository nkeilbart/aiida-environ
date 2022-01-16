from aiida.engine import BaseRestartWorkChain, WorkChain
from aiida.plugins import WorkflowFactory, CalculationFactory
from aiida.orm import StructureData, Dict, List, Int, Str, load_node, load_group

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
            EnvPwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `EnvPwBaseWorkChain`.'},
            exclude=('pw.structure')
        )
        spec.input('test_parameters', valid_type=Dict)
        spec.outline(
            cls.setup,
            cls.run_test,
            cls.display_results,
        )

    def setup(self):

        '''Setup default structure & parameters for testing. -- in progress'''

        # load environ parameters
        self.ctx.environ_parameters = self.inputs.base.pw.environ_parameters

        # local variables for setup
        difftypes = ('forward', 'backward', 'central')           # finite difference type tuple
        difforders = ('first', 'second')                         # finite difference order tuple
        axes = ('x', 'y', 'z')                                   # axis tuple
        nat = self.inputs.base.pw.parameters['CONTROL']['nat']   # set nat for random
        wild = random.randint(1, nat)                            # assign random index

        # 2 Si atoms - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in
        # FIXME not sure how to validate structure before base.pw excepts - don't want to load every time
        if self.inputs.base.pw['structure'] is None:
            cell = [[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]]
            structure = StructureData(cell=cell)
            structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
            structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')
            self.pw.structure = structure

        # validate pseudo string
        upfstr = self.inputs.test_parameters.pseudo
        try:
            upf = load_group(upfstr)
            self.inputs.base['pseudos'] = upf.get_pseudos(structure=self.inputs.base.pw['structure'])
        except:
            raise NameError(f'{upfstr} is not an imported pseudo family. Make sure to use aiida-pseudo plugin')

        # get user-input test parameters and set defaults
        chain_parameters = self.inputs.test_parameters.get_dict()
        chain_parameters.setdefault('multi', False)               # default move one atom at a time
        chain_parameters.setdefault('diff_type', 'central')       # default central difference
        chain_parameters.setdefault('diff_order', 'first')        # default first-order difference
        chain_parameters.setdefault('nsteps', 5)                  # default n = 5
        chain_parameters.setdefault('axis', wild)                 # default random direction (int)
        chain_parameters.setdefault('step', 0.1)                  # default dx = 0.1
        chain_parameters.setdefault(                              # default one random atom moved
            'move_list',
            [random.randint(1, nat)]
        )

        # validate user-input axis string
        axstr = self.inputs.test_parameters.axis
        if axstr in axes:
            self.inputs.test_parameters.axis = axes.index(axstr)
        else: # set default for garbage input
            print('\nAxis selection not valid. Setting to random axis')
            self.inputs.test_parameters.axis = wild
        self.ctx.axstr = axstr # useful for calc descriptions
        
        # validate user-input finite difference type
        typestr = self.inputs.test_parameters.diff_type
        if typestr in difftypes:
            self.inputs.test_parameters.diff_type = typestr
        else: # set default for garbage input
            print(f'{typestr} is not valid. Setting to central difference interpolation')
            self.inputs.test_parameters.diff_type = 'central'

        # validate user-input finite difference order
        ordstr = self.inputs.test_parameters.diff_order
        if ordstr in difforders:
            self.inputs.test_parameters.diff_order = ordstr
        else: # set default for garbage input
            print(f'{ordstr} is not valid. Setting to central finite difference')
            self.inputs.test_parameters.diff_order = 'first'

        # validate user-input tuple of atoms moved
        index_list = self.inputs.test_parameters.move_list
        valid_indices = *(int(i) for i in range(1, nat+1)),
        for index in index_list:
            if index not in valid_indices: # set default for garbage input
                print(f'\n{index} is not a valid atom index. Setting to first atom')
                self.inputs.test_parameters.move_list = (0)
                break

        self.inputs.test_parameters = Dict(dict=chain_parameters)

    def run_test(self):

        '''Displace an atom from initial position to compare forces. -- needs testing'''

        # test parameter variable block for logic legibility
        n = self.inputs.test_parameters.nsteps                  # total number of steps
        atoms = self.inputs.test_parameters.move_list           # tuple of ith atoms to move
        axis = self.inputs.test_parameters.axis                 # index of axis to perturb
        step = self.inputs.test_parameters.step                 # step size
        dtype = self.inputs.test_parameters.diff_type           # difference type
        multi = self.inputs.test_parameters.multi               # multi-atom perturb flag

        if multi:
            prefix = 'multi'

        # calculation dictionary -- len(calculations) = len(move_list)
        # calculations = {
        #   1 : [calcPK1, calcPK2, calcPK3, ..., calcPKn],
        #   ...,
        #   # : calclist
        # }
        self.ctx.calculations = {}

        # FIXME NEED TO DO HALF-STEP CALCULATIONS FOR CENTRAL DIFFERENCE TYPE -- 0.0, 0.5, 1.0, 1.5, 2.0 WHERE F(x=1) ~ (F(1.5)-F(0.5))/dh where dh = 1.0
        #if dtype == 'central':
        #   perform calculation at x = x + dx
        #   perform calculation at x = x + dx/2

        # perform test for each atom in move_list
        for atom in atoms:
        
            atom -= 1 # ith atom has index i-1
            
            if not multi:
                prefix = f'atom{atom}'

            for i in range(n):

                if i == 0: # initial calculation

                    # calculation identifiers
                    self.inputs.pw.metadata.description = 'Initial structure | d{} = {}'.format(self.ctx.axstr, i * step) # brief description
                    name = f'{prefix}.{axis}.0' # calculation node key in context dictionary

                else: # displaced atom calculations

                    # get initial calculation data
                    if i == 1: # only structure will change between calculations

                        initname = f'{prefix}.{self.ctx.axstr}.0' # assign previous calculation name
                        initcalc = load_node(self.ctx.calculations[initname]) # load previous calculation node

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
            self.ctx.calculations[atom+1] = [self.ctx[f'{prefix}.{self.ctx.axstr}.{k}'].pk for k in range(n)]

    def display_results(self): # quantitative (chart) & qualitative (plot)

        '''Compare finite difference forces against DFT forces -- needs testing'''

        diff_type = self.inputs.test_parameters.diff_type       # interpolation type string
        atoms = self.inputs.test_parameters.move_list           # index of atom perturbed
        step = self.inputs.test_parameters.step                 # step size float

        CompareCalculation = CalculationFactory('environ.compareF')

        results = {}
        for atom in atoms:

            calclist = self.ctx.calculations[atom]
            results[atom] = CompareCalculation(List(list=calclist), Str(diff_type), )

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
