from aiida.engine import WorkChain, ToContext, append_, calcfunction, submit
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.common import AttributeDict, exceptions
from aiida.orm import StructureData, ArrayData, List
import sys
sys.path.insert(1, '../../calculations')
from adsorbate_calc import AdsorbateCalculation
<<<<<<< HEAD
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
PwBaseWorkChain = WorkflowFactory('environ.pw.base')
=======

EnvPwCalculation = CalculationFactory('environ.pw')
# TODO copy the way that relax does this: expose inputs to base workchain instead of envpwcalc - see the notes I'll send separately
>>>>>>> 3b4eda8e5f8e57acea5d34dd4693d77ee9feb312

class AdsorbateSimulation(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
<<<<<<< HEAD
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'},
            exclude=('pw.structure'))
        spec.inputs('vacancies', valid_type=ArrayData)
=======
        spec.expose_inputs(EnvPwCalculation, namespace='pw',
            namespace_options={'help': 'Inputs for the `EnvPwCalculation`.'})
        spec.inputs('adsorbate_coords', valid_type=ArrayData)
>>>>>>> 3b4eda8e5f8e57acea5d34dd4693d77ee9feb312
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
<<<<<<< HEAD
        self.ctx.struct_list = AdsorbateCalculation(self.inputs.site_index, self.inputs.possible_adsorbates, self.inputs.adsorbate_index, self.inputs.structure, self.inputs.vacancies)
=======
        inputs = AttributeDict(self.exposed_inputs(EnvPwCalculation, namespace='pw'))
        inputs.environ_parameters = inputs.environ_parameters.get_dict()
        use_adsorbates = AdsorbateCalculation(self.inputs.site_index, self.inputs.possible_adsorbates, self.inputs.adsorbate_index)
        # Get the list of structures that should be used in calculations
        self.ctx.structures = ["""INPUT STRUCTURE"""] * len(use_adsorbates)
        for i, x in use_adsorbates:
            for j, y in x:
                for k, z in y:
                    if z != 0:
                        self.ctx.structures[i].append_atom(position=self.inputs.adsorbate_coords[j], symbols=z)
>>>>>>> 3b4eda8e5f8e57acea5d34dd4693d77ee9feb312
        

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