from aiida.engine import WorkChain, ToContext, append_
from aiida.plugins import WorkflowFactory
from aiida.common import AttributeDict
from aiida.orm import StructureData, List
from aiida_environ.calculations.adsorbate_calc import adsorbate_calculation
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida.orm.utils import load_node

PwBaseWorkChain = WorkflowFactory('environ.pw.base')

class AdsorbateGraphConfiguration(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            exclude=('clean_workdir', 'pw.structure', 'pw.parent_folder'),
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'})
        spec.input('vacancies', valid_type=List) # List of 3-tuples
        spec.input('site_index', valid_type=List) # List of ints
        spec.input('possible_adsorbates', valid_type=List) # List of structures
        spec.input('adsorbate_index', valid_type=List) # List of Lists of Ints
        spec.input('structure', valid_type=StructureData)
        spec.outline(
            cls.setup,
            cls.selection, 
            cls.simulate,
            cls.postprocessing
        )

    def setup(self):
        self.ctx.struct_list = []

    def selection(self):
        self.ctx.struct_list = adsorbate_calculation(
            self.inputs.site_index, self.inputs.possible_adsorbates, self.inputs.adsorbate_index, self.inputs.structure, self.inputs.vacancies)   

    def simulate(self):
        for structure_pk in self.ctx.struct_list:
            inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
            structure = load_node(structure_pk)
            self.report('{}'.format(structure))
            inputs.pw.structure = structure

            inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
            running = self.submit(PwBaseWorkChain, **inputs)

            self.report('launching PwBaseWorkChain<{}>'.format(running.pk))

        return ToContext(workchains=append_(running))
    
    def postprocessing(self):
        pass