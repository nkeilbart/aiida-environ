import numpy as np

from aiida.engine import WorkChain, ToContext, append_
from aiida.plugins import WorkflowFactory
from aiida.common import AttributeDict
from aiida.orm import StructureData, List, Dict
from aiida.orm.utils import load_node

from aiida_quantumespresso.utils.mapping import prepare_process_inputs

from aiida_environ.utils.vector import reflect_vacancies, get_struct_bounds
from aiida_environ.calculations.adsorbate.gen_supercell import adsorbate_gen_supercell, gen_hydrogen
from aiida_environ.data.charge import EnvironChargeData

PwBaseWorkChain = WorkflowFactory('environ.pw.base')

class AdsorbateGrandCanonical(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'},
            exclude=('pw.structure'))
        spec.inputs('vacancies', valid_type=List)
        spec.inputs('structure', valid_type=StructureData)
        spec.inputs('calculation_parameters', valid_type=Dict)
        spec.outline(
            cls.setup,
            cls.selection, 
            cls.simulate,
            cls.postprocessing
        )

    def setup(self):
        self.ctx.struct_list = []
        if 'charge_distance' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['charge_distance'] = 5.0
        if 'charge_max' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['charge_max'] = 1.0
        if 'charge_min' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['charge_min'] = -1.0
        if 'charge_increment' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['charge_increment'] = 0.2
        if 'charge_spread' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['charge_spread'] = 0.5
        if 'charge_axis' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['charge_axis'] = 3
        if 'cell_shape_x' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['cell_shape_x'] = 2
        if 'cell_shape_y' not in self.inputs.calculation_parameters:
            self.inputs.calculation_parameters['cell_shape_y'] = 2
        
        # TODO: chcek sanity of inputs

    def selection(self):
        axis = self.inputs.calculation_parameters['charge_axis']
        self.ctx.struct_list = adsorbate_gen_supercell(self.inputs.cell_shape, self.inputs.structure, self.inputs.vacancies)
        reflect_vacancies(self.ctx.struct_list, self.inputs.structure, axis)

    def simulate(self):
        axis = self.inputs.calculation_parameters['axis']
        charge_min = self.inputs.calculation_parameters['charge_min']
        charge_max = self.inputs.calculation_parameters['charge_max']
        charge_inc = self.inputs.calculation_parameters['charge_increment']
        charge_spread = self.inputs.calculation_parameters['charge_spread']
        charge_range = range(charge_min, charge_max+charge_inc, charge_inc)

        # TODO: maybe do this at setup and change the cell if it's too big?
        cpos1, cpos2 = get_struct_bounds(self.inputs.structure, axis)
        # change by 5 angstrom
        cpos1 -= 5.0
        cpos2 += 5.0
        npcpos1 = np.zeros(3)
        npcpos2 = np.zeros(3)
        npcpos1[axis-1] = cpos1
        npcpos2[axis-1] = cpos2

        nsims = (len(charge_range) * (len(self.ctx.struct_list) + 1)) + 1
        self.report(f'number of simulations to run = {nsims}')

        for charge_amt in charge_range:

            # loop over charges
            charges = EnvironChargeData()
            # get position of charge
            charges.append_charge(charge_amt/2, tuple(npcpos1), charge_spread, 2, axis)
            charges.append_charge(charge_amt/2, tuple(npcpos2), charge_spread, 2, axis)

            for structure_pk in self.ctx.struct_list:
                inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
                structure = load_node(structure_pk)
                self.report(f'{structure}')
                inputs.pw.structure = structure
                inputs.pw.external_charges = charges

                inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
                running = self.submit(PwBaseWorkChain, **inputs)

                self.report(f'launching PwBaseWorkChain<{running.pk}>')

            # base simulation
            inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
            structure = self.inputs.structure
            self.report(f'{structure}')
            inputs.pw.structure = structure
            inputs.pw.external_charges = charges

            inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
            running = self.submit(PwBaseWorkChain, **inputs)
            
            self.report(f'launching PwBaseWorkChain<{running.pk}>')

        # hydrogen simulation
        inputs = AttributeDict(self.exposed_inputs(PwBaseWorkChain, namespace='base'))
        structure = gen_hydrogen()
        self.report(f'{structure}')
        inputs.pw.structure = structure

        inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
        running = self.submit(PwBaseWorkChain, **inputs)

        self.report(f'launching PwBaseWorkChain<{running.pk}>')

        return ToContext(workchains=append_(running))
    
    def postprocessing(self):
        pass