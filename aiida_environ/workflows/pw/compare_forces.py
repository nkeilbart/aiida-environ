from aiida.orm import StructureData, QueryBuilder, Dict, List, Float, Str, load_group
from aiida.engine import WorkChain

from aiida_environ.calculations.energy_differentiate import calculate_finite_differences
from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain
from aiida_pseudo.groups.family.pseudo import PseudoPotentialFamily

import random

def _build_default_structure() -> StructureData:
        """Returns default StructureData - 2 Si atoms"""

        # aiida-qe test structure - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in

        structure = StructureData(
            cell=[[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]])
        structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
        structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')

        return structure


class CompareForcesWorkChain(WorkChain): 
    """WorkChain to evaluate EnvPwBaseWorkChain forces against finite difference forces"""

    types = ('forward', 'backward', 'central')  # finite difference type tuple
    orders = ('first', 'second')                # finite difference order tuple
    axes = ('x', 'y', 'z')                      # axis tuple

    @classmethod
    def define(cls, spec) -> None:
        """I/O specifications & WorkChain outline"""
        
        super().define(spec)

        # Input validation
        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace='base',
            namespace_options={
                'help': 'Inputs for the `FiniteForcesWorkChain`.'
            },
            exclude=('pw.structure','pw.pseudos',)
        )
        spec.input('structure', valid_type=StructureData, default=lambda: _build_default_structure())
        spec.input('pseudo_group', valid_type=Str, default=lambda: Str('SSSP/1.1/PBE/efficiency'), help='aiida-pseudo family string')
        spec.input(
            'test_settings',
            valid_type=Dict,
            required=True,
            help='Force test settings to increment atom_to_perturb by dr based on step_sizes [dx, dy, dz] and evaluate finite differences for n-steps'
        )
        spec.output('results', valid_type=Dict)

        # WorkChain logic
        spec.outline(
            cls.setup,
            cls.run_test,
            cls.get_results
        )

    def setup(self):
        '''Setup default structure & parameters for testing.'''

        natoms = len(self.inputs.structure.sites)  # nat for random
        wild = random.randint(1, natoms)           # random index

        # set default settings for missing keys
        settings_dict = self.inputs.test_settings.get_dict()
        settings_dict.setdefault('diff_type', 'forward')
        settings_dict.setdefault('diff_order', 'first')
        settings_dict.setdefault('atom_to_perturb', wild)
        settings_dict.setdefault('n_steps', 5)
        settings_dict.setdefault('step_sizes', [0.1, 0.0, 0.0])

        # validate inputs
        self._validate_pseudo_group()
        self._validate_diff_type()
        self._validate_diff_order()
        self._validate_atom_to_perturb(natoms)
        self._validate_n_steps(settings_dict['n_steps'])
        self._validate_step_sizes()

        self.inputs.test_settings = Dict(dict=settings_dict)

    def run_test(self):
        '''Displaces an atom_to_perturb from initial position, according to input test test_settings.'''

        # local variable block
        diff_order = self.inputs.test_settings['diff_order']
        diff_type = self.inputs.test_settings['diff_type']
        steps = self.inputs.test_settings['step_sizes']
        n = self.inputs.test_settings['n_steps'] + 1 # initial position + n-perturbations
        prefix = f'atom{self.atom}'

        # context variable block
        self.ctx.cell = self.inputs.structure.cell
        self.ctx.edge = self.inputs.structure.cell_lengths[self.atom]
        self.ctx.sites = self.inputs.structure.sites
        self.ctx.initial_position = self.ctx.sites[self.atom].position

        # central difference requires half-step increments
        if diff_type == 'central' and diff_order == 'first':
            n *= 2
            step = sum([(dh/2) ** 2 for dh in steps]) ** 0.5
        else:
            step = sum([dh ** 2 for dh in steps]) ** 0.5

        # submit calculations
        for i in range(n):
            chain_name = f'{prefix}.{self.ctx.axstr}.{i}'
            inputs = self._prepare_inputs(i, i * step)
            env_chain = self.submit(EnvPwBaseWorkChain, **inputs)
            self.to_context(**{chain_name: env_chain})

        # collect the WorkChains
        self.ctx.environ_chain_list = []
        for k in range(n):
            name = f'{prefix}.{self.ctx.axstr}.{k}'
            self.ctx.environ_chain_list.append(self.ctx[name].pk)

    def get_results(self): # quantitative (chart) & qualitative (plot)

        '''Compare finite difference forces against DFT forces, according to test test_settings -- needs testing'''

        results = calculate_finite_differences(
            List(list=self.ctx.environ_chain_list),
            self.inputs.test_settings
        )

        self.out('results', results)

    def _prepare_inputs(self, i: int, dr: float) -> dict:
        """Returns input dictionary ready for Process submission"""

        if i == 0:
            which = 'Initial'
        else:
            which = 'Perturbed'

        # TODO this function only exists because passing base inputs to new submits raises exceptions with exposed inputs

        inputs = {
            'pw': {
                'code': self.inputs.base.pw.code,
                'pseudos': self.ctx.pseudos,
                'parameters': self.inputs.base.pw.parameters,
                'environ_parameters': self.inputs.base.pw.environ_parameters,
                'metadata': {
                    'options': {
                        'resources': {
                            'num_machines': 1,
                            'num_mpiprocs_per_machine': 4}
                    }
                }
            },
            'metadata': {
                'description': f"{which} structure | Atom {self.atom+1} d{self.ctx.axstr} = {dr:.2f}",
            },
            'kpoints': self.inputs.base.kpoints
            #'automatic_parallelization': {
            #    'max_wallclock_seconds': 1800,
            #    'target_time_seconds': 600
            #    'max_num_machines': 2
            #}
        }

        if i == 0:
            inputs['pw']['structure'] = self.inputs.structure
        else:
            inputs['pw']['structure'] = self._perturb_atom(
                        i = i,
                        steps = self.inputs.test_settings['step_sizes']
                    )

        return inputs

    def _perturb_atom(self, i: int, steps: list) -> StructureData:
        """Returns StructureData with updated position"""
    
        new_position = [0., 0., 0.]

        # update position tuple
        for j in range(3):
            
            if steps[j] != 0.0:
            
                new_position[j] = self.ctx.initial_position[j] + i * steps[j]

                if (self.ctx.edge - new_position[j]) > 0.001:
                    continue
                else:
                    raise Exception('\nNew atom_to_perturb position appears to be outside cell bounds. Stopping.')

            else:
                new_position[j] = self.ctx.initial_position[j]

        new_structure = StructureData(cell=self.ctx.cell) # NEW STRUCTURE HAS 

        # TODO index existing StructureData for one-to-one Site replacement?
        for k in range(len(self.ctx.sites)):

            if k == self.atom:
                new_structure.append_atom(
                    position=new_position,
                    symbols=self.ctx.sites[k].kind_name
                )
            
            else:
                new_structure.append_atom(
                    position=self.ctx.sites[k].position,
                    symbols=self.ctx.sites[k].kind_name
                )

        return new_structure

    def _validate_pseudo_group(self):
        """Validates pseudopotential family input"""
        
        qb = QueryBuilder()
        qb.append(
            PseudoPotentialFamily,
            project='label'
        )

        group = self.inputs.pseudo_group.value

        # pseudo family validation
        if group in qb.all(flat=True):
            upf = load_group(group)
        else:
            print(f"\n{group} is not in aiida-pseudo families")
            upf = load_group('SSSP/1.1/PBE/efficiency')

        self.ctx.pseudos = upf.get_pseudos(structure=self.inputs.structure)

    def _validate_diff_type(self):
        """Validate finite difference type input"""

        type_str = self.inputs.test_settings['diff_type']

        # type validation
        if not isinstance(type_str, str):
            raise Exception("\ndiff_type must be 'forward', 'backward', or 'central'")

        # string validation
        if type_str in self.types:
            self.inputs.test_settings.diff_type = type_str        
        else:
            print(f'\n{type_str} is not valid. Setting to central difference interpolation')
            self.inputs.test_settings.diff_type = 'central'

    def _validate_diff_order(self):
        """Validates finite difference order input"""

        ord_str = self.inputs.test_settings['diff_order']

        # type validation        
        if not isinstance(ord_str, str):
            raise Exception("\ndiff_order must be 'first' or 'second'")

        if ord_str in self.orders:
            self.inputs.test_settings.diff_order = ord_str
        else:
            print(f'{ord_str} is not valid. Setting to first-order finite difference')
            self.inputs.test_settings.diff_order = 'first'

    def _validate_step_sizes(self):
        """Validates step size input"""

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

        # direction validation
        if steplist.count(0.0) == 2:
            for step in steplist:
                if step != 0.0: direction = steplist.index(step)
            self.ctx.axstr = self.axes[direction]
        elif steplist.count(0.0) == 3: # set default for garbage input
            print('\nStep size in every direction is 0. Setting to dx = 0.1')
            self.inputs.test_settings['step_sizes'] = [0.01, 0.0, 0.0]
            self.ctx.axstr = 'x'
        else:
            self.ctx.axstr = 'r'

    def _validate_atom_to_perturb(self, nat):
        """Validates atom index input"""

        atom = self.inputs.test_settings['atom_to_perturb']

        # type validation
        if not isinstance(atom, int):
            raise Exception('\natom_to_perturb must be an integer')

        # magnitude validation
        if atom < 0 or atom > nat:
            raise Exception('\nAtom index must be greater than zero and less than number of atoms. Setting to first atom')

        self.atom = atom - 1

    def _validate_n_steps(self, n):
        """Validates total number of steps input"""

        # type validation
        if not isinstance(n, int):
            raise Exception('\nn_steps must be an int')

        diff_order = self.inputs.test_settings['diff_order']

        if diff_order == 'second' and n < 2:
            raise Exception('\nMininum 2 steps required for second-order forward/backward finite differences. Setting n_steps = 2')