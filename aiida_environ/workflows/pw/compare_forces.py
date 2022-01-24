from aiida.orm import StructureData, Dict, List, Float, Str, load_node, load_group
from aiida.engine import WorkChain

from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain
from aiida_environ.calculations.finite import calculate_finite_differences

import random

def _build_default_structure() -> StructureData:
        """Returns default StructureData - 2 Si atoms"""

        # aiida-qe test structure - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in

        structure = StructureData(
            cell=[[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]])
        structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
        structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')

        return structure


class FiniteForcesWorkChain(WorkChain): 
    """  """

    types = ('forward', 'backward', 'central')  # finite difference type tuple
    orders = ('first', 'second')                # finite difference order tuple
    axes = ('x', 'y', 'z')                      # axis tuple

    @classmethod
    def define(cls, spec) -> None:
        """   """
        
        super().define(spec)

        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace='base',
            namespace_options={'help': 'Inputs for the `FiniteForcesWorkChain`.'},
            exclude=('pw.structure','pw.pseudos',)
        )

        spec.input('structure', valid_type=StructureData, default=lambda: _build_default_structure())
        spec.input('pseudo_group', valid_type=Str, default=lambda: Str('SSSP/1.1/PBE/efficiency'))
        spec.input('test_settings', valid_type=Dict, required=True)

        spec.outline(
            cls.setup,
            cls.validate_test_settings,
            cls.run_test,
            cls.display_results
        )

    def _validate_diff_type(cls, self):
        """-1"""

        type_str = self.inputs.test_settings['diff_type']

        # type validation
        if not isinstance(type_str, str):
            raise Exception("\ndiff_type must be 'forward', 'backward', or 'central'")

        # string validation
        if type_str in cls.types:
            self.inputs.test_settings.diff_type = type_str        
        else:
            print(f'\n{type_str} is not valid. Setting to central difference interpolation')
            self.inputs.test_settings.diff_type = 'central'

    def _validate_diff_order(cls, self):

        ord_str = self.inputs.test_settings['diff_order']

        # type validation        
        if not isinstance(ord_str, str):
            raise Exception("\ndiff_order must be 'first' or 'second'")

        if ord_str in cls.orders:
            self.inputs.test_settings.diff_order = ord_str
        else:
            print(f'{ord_str} is not valid. Setting to first-order finite difference')
            self.inputs.test_settings.diff_order = 'first'

    def _validate_step_sizes(cls, self):
        """-1"""

        steplist = self.inputs.test_settings['step_sizes']

        # type validation
        if not isinstance(steplist, list):
            raise Exception('\nstep_sizes must be a list of 3 floats')

        # length validation
        if len(steplist) != 3:
            raise Exception('\nAxis tuple must have 3 elements: [dx, dy, dz]')

        # element type validation
        for dh in steplist:
            if not isinstance(dh, float): raise Exception(f'\nStep list may only contain float values')

        # magnitude validation
        if steplist.count(0.0) == 1:
            self.ctx.axstr = cls.axes[steplist.index(0.0)]
        elif steplist.count(0.0) == 3: # set default for garbage input
            print('\nStep size is 0. Setting to dx = 0.1')
            self.inputs.test_settings['step_sizes'] = [0.01, 0.0, 0.0]
            self.ctx.axstr = 'x'
        else:
            self.ctx.axstr = 'r'

    def _validate_atom_to_move(self):
        """-1"""

        atom = self.inputs.test_settings['atom_to_move']

        # type validation
        if not isinstance(atom, int):
            raise Exception('\natom_to_move must be an integer')

        # magnitude validation
        nat = len(self.inputs.structure.sites)
        if atom < 0 or atom > nat:
            raise Exception('\nAtom index must be greater than zero and less than number of atoms')

    def _validate_nsteps(self):
        """-1"""

        # type validation
        if not isinstance(self.inputs.nsteps, int):
            raise Exception('\nnsteps must be an int')

    def _prepare_new_inputs(self, i: int, dh: float) -> dict:
        """Returns input dictionary ready for Process submission"""

        inputs = {
            'pw': {
                'code': self.inputs.base.pw.code,
                'structure': self._perturb_atom(),
                'pseudos': self.inputs.base.pseudos,
                'metadata': {
                    'description': 'Perturbed structure | d{} = {:.2}'.format(self.ctx.axstr, i * dh)
                }
            },
            'kpoints': self.inputs.base.pw.kpoints,
            'environ_parameters': self.inputs.base.environ_parameters
        }

        return inputs

    def _perturb_atom(self, atom: int, i: int, steps: list) -> StructureData:
        """Returns StructureData with updated position"""
    
        new_position = (0., 0., 0.)

        # update position tuple
        for j in range(3):
            
            if steps[j] != 0.0:
            
                new_position[j] = self.ctx.initial_position[j] + i * steps[j]

                if (self.ctx.edge - new_position[j]) > 0.001:
                    continue
                else:
                    raise Exception('\nNew atom_to_move position appears to be outside cell bounds. Stopping.')

            else:
                new_position[j] = self.ctx.initial_position[j]

        new_structure = StructureData(cell=self.ctx.cell)

        # build new StructureData
        for k in range(len(self.ctx.sites)):

            if k == atom:
                new_structure.append_atom_to_move(
                    position=new_position,
                    symbols=self.ctx.sites[k].kind_name
                )
            
            else:
                new_structure.append_atom_to_move(
                    position=self.ctx.sites[k].position,
                    symbols=self.ctx.sites[k].kind_name
                )

        return new_structure

    def setup(self):
        '''Setup default structure & parameters for testing. -- testing needed'''

        nat = len(self.inputs.structure.sites)  # nat for random
        wild = random.randint(1, nat)           # random index

        # get user-input test parameters and set defaults
        settings_dict = self.inputs.test_settings.get_dict()
        settings_dict.setdefault('diff_type', 'central')            # default central difference
        settings_dict.setdefault('diff_order', 'first')             # default first-order difference
        settings_dict.setdefault('atom_to_move', wild)              # default random atom_to_move moved
        settings_dict.setdefault('nsteps', 5)                       # default n = 5
        settings_dict.setdefault('step_sizes', [0.1, 0.0, 0.0])     # default dr = dx = 0.1

        self.inputs.test_settings = Dict(dict=settings_dict)

    def validate_test_settings(self): # TODO move validation blocks to /utils/validate.py?

        '''Validate test test_settings with exception handling. -- testing needed'''

        # local variables for validation # TODO add validation for atom_to_move & nsteps?

        upf = load_group(self.inputs.pseudo_group)
        self.inputs.base.pw.structure = self.inputs.structure
        self.inputs.base.pseudos = upf.get_pseudos(structure=self.inputs.base.pw.structure)

        self._validate_diff_type()
        self._validate_diff_order()
        self._validate_atom_to_move()
        self._validate_nsteps()
        self._validate_step_sizes()

    def run_test(self):
        '''Displaces an atom_to_move from initial position, according to input test test_settings. -- needs testing'''

        # local variable block
        atom = self.inputs.test_settings['atom_to_move'] - 1    # ith atom_to_move to move has index i-1
        diff_type = self.inputs.test_settings['diff_type']      # difference type
        steps = self.inputs.test_settings['step_sizes']         # list of step sizes
        n = self.inputs.test_settings['nsteps'] + 1             # initial position + n-perturbations

        self.ctx.prefix = f'atom{atom}'

        if diff_type == 'central': n *= 2 # central difference requires half-step calculations

        for i in range(n):

            # central difference requires half-step increments
            if diff_type == 'central':

                step = sum([(dh/2) ** 2 for dh in steps]) ** 0.5
            
            else:
            
                step = sum([dh ** 2 for dh in steps]) ** 0.5

            if i == 0: # initial calculation

                calcname = f'{self.ctx.prefix}.{self.ctx.axis}.0'
                self.inputs.base.pw['metadata']['description'] = \
                    'Initial structure | d{} = {:.2}'.format(self.ctx.axstr, i * step)

                calc = self.submit(EnvPwBaseWorkChain, **self.inputs.base)

                # assign data needed to context
                self.ctx.cell = self.inputs.structure.cell
                self.ctx.edge = self.inputs.structure.cell_lengths[atom]
                self.ctx.sites = self.inputs.structure.sites
                self.ctx.initial_position = self.ctx.sites[atom].position

            else: # perturbed atom calculation

                calcname = f'{self.ctx.prefix}.{self.ctx.axstr}.{i}'
                inputs = self._prepare_builder(i, i * step)
                
                calc = self.submit(EnvPwBaseWorkChain, **inputs)

            self.to_context(**{calcname: calc})

        # collect the calculation pks for this atom_to_move's test series using key convention
        self.ctx.calculations = [self.ctx[f'{self.ctx.prefix}.{self.ctx.axstr}.{k}'].pk for k in range(n)]

    def display_results(self): # quantitative (chart) & qualitative (plot)

        '''Compare finite difference forces against DFT forces, according to test test_settings -- needs testing'''

        diff_type = self.inputs.test_settings['diff_type']       # difference type string
        diff_order = self.inputs.test_settings['diff_order']     # difference order string
        atom = self.inputs.test_settings['atom_to_move']         # index of atom_to_move perturbed
        steps = self.inputs.test_settings['step_sizes']          # list of steps
        step = sum([dh ** 2 for dh in steps]) ** 0.5             # step size -- same for all difference types

        calclist = self.ctx.calculations
        results = calculate_finite_differences(
            List(list=calclist),
            Float(step),
            Str(diff_type),
            Str(diff_order)
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
