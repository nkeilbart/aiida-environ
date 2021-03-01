from aiida.engine import WorkChain, ToContext, append_, calcfunction
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.common import AttributeDict, exceptions
from aiida.orm import StructureData, ArrayData, List
import sys
sys.path.insert(1, '../../calculations')
from adsorbate_calc import AdsorbateCalculation

EnvPwCalculation = CalculationFactory('environ.pw')

class AdsorbateSimulation(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(EnvPwCalculation, namespace='pw',
            namespace_options={'help': 'Inputs for the `EnvPwCalculation`.'})
        spec.inputs('vacancies', valid_type=ArrayData)
        spec.inputs('site_index', valid_type=List) # List of ints
        spec.inputs('possible_adsorbates', valid_type=List) # List of structures
        spec.inputs('adsorbate_index', valid_type=List) # List of Lists of Ints
        spec.outline(
            cls.setup,
            cls.selection, 
            cls.simulate,
            cls.postprocessing
        )

    def setup(self):
        pass

    def selection(self):
        """ FIXME: I am not sure how to go from vacancies (coords) to site_index so for now, assume every vacancy is its own site
        """
        site_index = [i for i, c in enumerate(self.inputs.vacancies)]
        use_adsorbates = AdsorbateCalculation(site_index, self.inputs.possible_adsorbates, self.inputs.adsorbate_index)
        # Get the list of structures that should be used in calculations
        self.ctx.structures = ["""INPUT STRUCTURE"""] * len(use_adsorbates)
        for i, x in use_adsorbates:
            for j, y in x:
                for k, z in y:
                    if z != 0:
                        self.ctx.structures[i].append_atom(position=self.inputs.vacancies[j], symbols=z)
        
    def simulate(self):
        pass
    
    def postprocessing(self):
        pass