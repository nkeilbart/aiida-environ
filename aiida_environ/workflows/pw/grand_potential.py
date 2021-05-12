from aiida.engine import WorkChain, ToContext, append_, calcfunction, submit
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.common import AttributeDict, exceptions
from aiida.orm import StructureData, ArrayData, List
from aiida_environ.calculations.adsorbate_vec import reflect_vacancies
from aiida_environ.calculations.adsorbate_gen import generate_structures, generate_hydrogen
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida.orm.utils import load_node

PwBaseWorkChain = WorkflowFactory('environ.pw.base')

class AdsorbateGrandPotential(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'},
            exclude=('pw.structure'))
        spec.inputs('vacancies', valid_type=List)
        spec.inputs('structure', valid_type=StructureData)
        spec.inputs('cell_shape', valid_type=List)
        spec.outline(
            cls.setup,
            cls.selection, 
            cls.simulate,
            cls.postprocessing
        )

    def setup(self):
        self.ctx.struct_list = []

    def selection(self):
        self.ctx.struct_list = generate_structures(self.inputs.cell_shape, self.inputs.structure, self.inputs.vacancies)
        reflect_vacancies(self.ctx.struct_list, self.inputs.structure)

    def simulate(self):
        for structure_pk in self.ctx.struct_list:
            inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
            structure = load_node(structure_pk)
            self.report('{}'.format(structure))
            inputs.pw.structure = structure

            inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
            running = self.submit(PwBaseWorkChain, **inputs)

            self.report('launching PwBaseWorkChain<{}>'.format(running.pk))

        # base simulation
        inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
        structure = self.inputs.structure
        self.report('{}'.format(structure))
        inputs.pw.structure = structure

        # hydrogen simulation
        inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
        structure = generate_hydrogen()
        self.report('{}'.format(structure))
        inputs.pw.structure = structure

        inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
        running = self.submit(PwBaseWorkChain, **inputs)

        self.report('launching PwBaseWorkChain<{}>'.format(running.pk))

        return ToContext(workchains=append_(running))
    
    def postprocessing(self):
        pass