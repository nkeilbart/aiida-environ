from aiida.engine import WorkChain, ToContext, append_, calcfunction
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.common import AttributeDict, exceptions
from aiida.orm import StructureData, ArrayData, List

EnvPwCalculation = CalculationFactory('environ.pw')

class AdsorbateSimulation(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(EnvPwCalculation, namespace='pw',
            namespace_options={'help': 'Inputs for the `EnvPwCalculation`.'})
        spec.inputs('Vacancies', valid_type=ArrayData)
        spec.inputs('Site_Index', valid_type=List) # List of ints
        spec.inputs('Possible_Adsorbates', valid_type=List) # List of structures
        spec.inputs('Adsorbate_Index', valid_type=List) # List of Lists of Ints
        spec.outline(
            cls.setup,
        )

    def setup(self):
        pass