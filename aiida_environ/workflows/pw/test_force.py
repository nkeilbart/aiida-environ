from aiida.engine import WorkChain, append_
from aiida.plugins import WorkflowFactory
from aiida.orm import StructureData, Dict, load_node
#import random # TODO add randomizing option

EnvPwBaseWorkChain = WorkflowFactory('environ.pw.base')

class EnvPwForceTest(WorkChain):

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

    def setup(self): # initial calculation

        '''Setup default structure & parameters for testing. -- in progress'''

        # 2 Si atoms - aiida-quantumespresso/tests/calculations/test_pw/test_default_pw.in
        cell = [[2.715, 0, 2.715], [0, 2.715, 2.715], [2.715, 2.715, 0]]
        structure = StructureData(cell=cell)
        structure.append_atom(position=(0., 0., 0.), symbols='Si', name='Si')
        structure.append_atom(position=(1.3575, 1.3575, 1.3575), symbols='Si', name='Si')
        self.pw.structure = structure

        self.ctx.environ_parameters = self.inputs.base.pw.environ_parameters
        parameters = self.inputs.test_parameters.get_dict()
        parameters.setdefault('perturbed', 0)               # default first atom moved #TODO change to tuple for multiple-atom translation; random option
        parameters.setdefault('nsteps', 5)                  # default n = 5
        parameters.setdefault('axis', 0)                    # default x-direction #TODO change to tuple for multiple-atom translation; random option
        parameters.setdefault('step', 0.1)                  # default dx = 0.1
        self.inputs.test_parameters = Dict(dict=parameters)
        
        return

    def run_test(self): # displacement & interpolation

        '''Displace an atom from initial position to compare forces. -- in progress'''

        for i in range(self.inputs.test_parameters.nsteps):

            displacement = (0., 0.) # tracks atom displacement from initial position

            if i == 0:

                self.pw.metadata.label = 'Initial structure | {}'.format(displacement)

            else:

                # attribute variable block
                atom = self.inputs.test_parameters.perturbed        # index of atom perturbed
                axis = self.inputs.test_parameters.axis             # index of axis to perturb
                step = self.inputs.test_parameters.step             # step size
                cell = self.ctx.initial.inputs.structure.cell       # unit cell of structure
                sites = self.ctx.initial.inputs.structure.sites     # tuple of atom positions
                
                # local variable block
                displacement[atom] = i * step                       # track displacement
                position = sites[atom].position                     # atom position
                testpos = (position[0] + step,) + position[1:]      # perturb atom
                edge = calc.inputs.structure.cell_lengths[atom]     # max cell length

                self.pw.metadata.label = 'Perturbed structure | {}'.format(displacement)

                if (edge - position[0]) > 0.001: # keep particle within cell
    
                    sites[atom].position = testpos # update array

                    prevcalc = load_node(self.ctx.calculations[i-1]) # load previous calc for inputs

                    builder = EnvPwBaseWorkChain.get_builder()
                    builder.code = prevcalc.inputs.base.pw.code
                    builder.pseudos = prevcalc.inputs.base.pw.pseudos
                    builder.kpoints = prevcalc.inputs.base.pw.kpoints
                    builder.parameters = prevcalc.inputs.base.pw.environ_parameters
                    builder.settings = calc.inputs.base.settings # KPOINTS gamma

                    structure = StructureData(cell=cell)
                    for j in range(len(sites)):
                        structure.append_atom(position=sites[j].position, symbols=sites[j].kind_name)
                    builder.structure = structure
                    
                else:

                    print('New atom position may be outside cell bounds')
                    quit()

            calc = self.submit(EnvPwBaseWorkChain, **self.ctx.environ_parameters)
            self.to_context(calculations=append_(calc))

    def display_results(self): # quantitative (chart) & qualitative (plot)
        '''Compare finite difference forces against DFT forces -- not started'''



        return


# need to add entry points to setup.json