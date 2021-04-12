from aiida.engine import WorkChain, ToContext, append_, calcfunction, submit
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.common import AttributeDict, exceptions
from aiida.orm import StructureData, ArrayData, List
from aiida_environ.calculations.adsorbate_vec import reflect_vacancies # FIXME: These should be calcfunctions being called
from aiida_environ.calculations.adsorbate_gen import gen_structures
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
PwBaseWorkChain = WorkflowFactory('environ.pw.base')

class AdsorbateGrandPotential(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'},
            exclude=('pw.structure'))
        spec.inputs('vacancies', valid_type=ArrayData)
        spec.inputs('structure', valid_type=StructureData)
        spec.outline(
            cls.setup,
            cls.selection, 
            cls.simulate,
            cls.postprocessing
        )

    def setup(self):
        self.ctx.struct_list = None

    def selection(self):
        self.ctx.reflected_vacancies = reflect_vacancies(self.inputs.structure, self.inputs.vacancies)
        self.ctx.struct_list = gen_structures(self.inputs.structure.cell.shape, self.inputs.structure, self.ctx.reflected_vacancies) # FIXME: Not sure how to get size of cell


    def simulate(self):
        inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
        for structure in self.ctx.struct_list:
            self.submit(PwBaseWorkChain, **inputs)
            inputs.pw.structure = structure

            inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
            running = self.submit(PwBaseWorkChain, **inputs)

            self.report('launching PwBaseWorkChain<{}>'.format(running.pk))

            return ToContext(workchains=append_(running))
    
    def postprocessing(self):
        pass