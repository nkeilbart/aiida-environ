from aiida.engine import BaseRestartWorkChain, WorkChain
from aiida.plugins import WorkflowFactory, CalculationFactory
from aiida.orm import StructureData, Dict, List, Int, load_node

from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin, recursive_merge

#import random # TODO add randomizing option

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

        # FIXME need to check inputs

        # 2 Si atoms - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in
        cell = [[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
        structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')
        self.pw.structure = structure

        # FIXME require user to enter pseudo? -- look for pseudo group; use get_pseudos(structure=structure)
        
        self.ctx.environ_parameters = self.inputs.base.pw.environ_parameters
        chain_parameters = self.inputs.test_parameters.get_dict()
        chain_parameters.setdefault('multi', False)               # default move one atom at a time
        chain_parameters.setdefault('perturbed', 0)               # default first atom moved #TODO change to tuple for multiple-atom translation; random option
        chain_parameters.setdefault('nsteps', 5)                  # default n = 5
        chain_parameters.setdefault('axis', 0)                    # default x-direction #TODO change to tuple for multiple-atom translation; random option
        chain_parameters.setdefault('step', 0.1)                  # default dx = 0.1
        self.inputs.test_parameters = Dict(dict=chain_parameters)

    def run_test(self):

        '''Displace an atom from initial position to compare forces. -- needs testing'''

        # test parameter variable block for logic legibility
        n = self.inputs.test_parameters.nsteps              # total number of steps
        atom = self.inputs.test_parameters.perturbed        # index of atom perturbed
        axis = self.inputs.test_parameters.axis             # index of axis to perturb
        step = self.inputs.test_parameters.step             # step size
        multi = self.inputs.test_parameters.multi           # multi-atom perturb flag

        if multi:
            prefix = 'multi'
        else:
            prefix = 'single'

        # identifier variables
        axnames = ['x', 'y', 'z'] # axis strings
        displacement = (0., 0.) # displaced atom tuple # TODO make dynamic

        for i in range(n):

            if i == 0: # initial calculation

                # calculation identifiers
                self.pw.metadata.description = 'Initial structure | {}'.format(displacement) # brief description
                name = f'{prefix}.{axnames[axis]}.0' # calculation node key in context dictionary

            else: # displaced atom calculations

                # get initial calculation data
                if i == 1: # only structure will change between calculations

                    initname = f'{prefix}.{axnames[axis]}.0' # assign previous calculation name
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
                displacement[atom] = i * step # update displacement tuple
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
                    builder.metadata.description = 'Perturbed structure | {}'.format(displacement)
                    
                    name = f'{prefix}.{axnames[axis]}.{i * step}'

                    # add structure to builder
                    structure = StructureData(cell=cell)
                    for j in range(len(sites)):
                        structure.append_atom(position=sites[j].position, symbols=sites[j].kind_name)
                    builder.structure = structure
                    
                else:

                    print('New atom position may be outside cell bounds')
                    quit()

            # submit calculations in parallel
            calc = self.submit(EnvPwBaseWorkChain, **self.ctx.environ_parameters)
            self.to_context(**{name: calc})

        # collect calculation pks using key convention for next step
        self.ctx.calclist = [self.ctx[f'{prefix}.{axnames[axis]}.{k}'].pk for k in range(n)]

    def display_results(self): # quantitative (chart) & qualitative (plot)

        '''Compare finite difference forces against DFT forces -- needs testing'''

        calcs = self.ctx.calclist                           # list of calc pks
        atom = self.inputs.test_parameters.perturbed        # index of atom perturbed
        axis = self.inputs.test_parameters.axis             # index of axis to perturb

        CompareCalculation = CalculationFactory('environ.compareF')
        results = CompareCalculation(List(list=calcs), Int(atom), Int(axis))

        # calculation parameters
        print()
        print(f'atom number = {atom+1}')
        print(f'axis        = {axis}     ( 0-x | 1-y | 2-z )')
        print(f'dh          = {self.inputs.test_parameters.step}')
        #print(f'environ     = {use_environ}')
        #print(f'doublecell  = {double_cell}')

        print(results)

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
