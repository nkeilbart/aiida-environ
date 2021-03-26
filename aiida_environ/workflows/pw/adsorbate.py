from aiida.engine import WorkChain, ToContext, append_, calcfunction, submit
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.common import AttributeDict, exceptions
from aiida.orm import StructureData, ArrayData, List
import sys
sys.path.insert(1, '../../calculations')
from adsorbate_calc import AdsorbateCalculation
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
PwBaseWorkChain = WorkflowFactory('environ.pw.base')

class AdsorbateGraphConfiguration(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'},
            exclude=('pw.structure'))
        spec.inputs('vacancies', valid_type=ArrayData)
        spec.inputs('site_index', valid_type=List) # List of ints
        spec.inputs('possible_adsorbates', valid_type=List) # List of structures
        spec.inputs('adsorbate_index', valid_type=List) # List of Lists of Ints
        spec.inputs('structure', valid_type=StructureData)
        spec.outputs('struct_list', valid_type=List)
        spec.outline(
            cls.setup,
            cls.selection, 
            cls.simulate,
            cls.postprocessing
        )

    def setup(self):
        self.ctx.struct_list = None

    def selection(self):
        self.ctx.struct_list = AdsorbateCalculation(self.inputs.site_index, self.inputs.possible_adsorbates, self.inputs.adsorbate_index, self.inputs.structure, self.inputs.vacancies)

        

    def simulate(self):
        inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
        for structure in self.outputs.struct_list:
            self.submit(PwBaseWorkChain, **inputs)
            inputs.pw.structure = structure

            inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
            running = self.submit(PwBaseWorkChain, **inputs)

            self.report('launching PwBaseWorkChain<{}>'.format(running.pk))

            return ToContext(workchains=append_(running))
    
    def postprocessing(self):
        pass