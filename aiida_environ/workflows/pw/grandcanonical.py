import numpy as np

from aiida.engine import WorkChain, ToContext, append_
from aiida.plugins import WorkflowFactory
from aiida.common import AttributeDict
from aiida.orm import StructureData, List, Dict
from aiida.orm.utils import load_node

from aiida_quantumespresso.utils.mapping import prepare_process_inputs

from aiida_environ.utils.vector import reflect_vacancies, get_struct_bounds
from aiida_environ.utils.charge import get_charge_range
from aiida_environ.calculations.adsorbate.gen_supercell import adsorbate_gen_supercell, gen_hydrogen
from aiida_environ.calculations.adsorbate.post_supercell import adsorbate_post_supercell
from aiida_environ.data.charge import EnvironChargeData

EnvPwBaseWorkChain = WorkflowFactory('environ.pw.base')
PwBaseWorkChain = WorkflowFactory('quantumespresso.pw.base')

class AdsorbateGrandCanonical(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(EnvPwBaseWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `EnvPwBaseWorkChain`.'},
            exclude=('pw.structure', 'pw.external_charges'))
        spec.input('vacancies', valid_type=List)
        spec.input('bulk_structure', valid_type=StructureData)
        spec.input('mono_structure', valid_type=StructureData)
        spec.input('calculation_parameters', valid_type=Dict)
        spec.outline(
            cls.setup,
            cls.selection, 
            #cls.simulate,
            #cls.postprocessing
        )

    def setup(self):
        self.ctx.num_adsorbate = []
        self.ctx.struct_list = []
        self.ctx.calculation_details = {}
        calculation_parameters = self.inputs.calculation_parameters.get_dict()
        calculation_parameters.setdefault('charge_distance', 5.0)
        calculation_parameters.setdefault('charge_max', 1.0)
        calculation_parameters.setdefault('charge_min', -1.0)
        calculation_parameters.setdefault('charge_increment', 0.2)
        calculation_parameters.setdefault('charge_spread', 0.5)
        calculation_parameters.setdefault('charge_axis', 3)
        calculation_parameters.setdefault('charge_dim', 2)
        calculation_parameters.setdefault('cell_shape_x', 2)
        calculation_parameters.setdefault('cell_shape_y', 2)
        self.ctx.calculation_parameters = Dict(dict=calculation_parameters)
        
        # TODO: check sanity of inputs

    def selection(self):
        axis = self.ctx.calculation_parameters['charge_axis']
        self.ctx.struct_list, self.ctx.num_adsorbate = adsorbate_gen_supercell(
                self.ctx.calculation_parameters, self.inputs.mono_structure, self.inputs.vacancies)
        reflect_vacancies(self.ctx.struct_list, self.inputs.structure, axis)

        self.report(f'struct_list written: {self.ctx.struct_list}')
        self.report(f'num_adsorbate written: {self.ctx.num_adsorbate}')

    def simulate(self):
        axis = self.ctx.calculation_parameters['axis']
        charge_max = self.ctx.calculation_parameters['charge_max']
        charge_inc = self.ctx.calculation_parameters['charge_increment']
        charge_spread = self.ctx.calculation_parameters['charge_spread']
        charge_range = self.get_charge_range(charge_max, charge_inc)

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

        for i, charge_amt in enumerate(charge_range):

            self.ctx.calculation_details[charge_amt] = {}

            # loop over charges
            charges = EnvironChargeData()
            # get position of charge
            charges.append_charge(charge_amt/2, tuple(npcpos1), charge_spread, 2, axis)
            charges.append_charge(charge_amt/2, tuple(npcpos2), charge_spread, 2, axis)

            for j, structure_pk in enumerate(self.ctx.struct_list):
                inputs = AttributeDict(self.exposed_inputs(EnvPwBaseWorkChain, namespace='base'))
                inputs.pw.parameters = inputs.pw.parameters.get_dict()
                structure = load_node(structure_pk)
                self.report(f'{structure}')
                inputs.pw.structure = structure
                inputs.pw.parameters["SYSTEM"]["tot_charge"] = charge_amt
                inputs.pw.external_charges = charges

                # Set the `CALL` link label
                inputs.metadata.call_link_label = f's{j}.c{i}'

                inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
                running = self.submit(EnvPwBaseWorkChain, **inputs)

                self.report(f'<s{j}.c{i}> launching EnvPwBaseWorkChain<{running.pk}>')
                self.ctx.calculation_details[charge_amt][structure_pk] = running.pk

            # base monolayer simulation
            inputs = AttributeDict(self.exposed_inputs(EnvPwBaseWorkChain, namespace='base'))
            structure = self.inputs.mono_structure
            self.report(f'{structure}')
            inputs.pw.structure = structure
            inputs.pw.external_charges = charges

            # Set the `CALL` link label
            inputs.metadata.call_link_label = f'smono.c{i}'

            inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
            running = self.submit(EnvPwBaseWorkChain, **inputs)
            
            self.report(f'<smono.c{i}> launching EnvPwBaseWorkChain<{running.pk}>')
            self.ctx.calculation_details[charge_amt]["mono"] = running.pk

        # bulk simulation
        inputs = AttributeDict(self.exposed_inputs(EnvPwBaseWorkChain, namespace='base'))
        delattr(inputs, 'environ_parameters')
        structure = self.inputs.bulk_structure
        self.report(f'{structure}')
        inputs.pw.structure = structure

        # Set the `CALL` link label
        inputs.metadata.call_link_label = f'sbulk.c{i}'

        inputs = prepare_process_inputs(PwBaseWorkChain, inputs)
        running = self.submit(PwBaseWorkChain, **inputs)
        
        self.report(f'<sbulk.c{i}> launching PwBaseWorkChain<{running.pk}>')
        self.ctx.calculation_details["bulk"] = running.pk

        # hydrogen simulation
        inputs = AttributeDict(self.exposed_inputs(EnvPwBaseWorkChain, namespace='base'))
        structure = gen_hydrogen()
        self.report(f'{structure}')
        inputs.pw.structure = structure

        # Set the `CALL` link label
        inputs.metadata.call_link_label = 'sads.neutral'

        inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
        running = self.submit(EnvPwBaseWorkChain, **inputs)

        self.report(f'<sads.neutral> launching EnvPwBaseWorkChain<{running.pk}>')
        self.ctx.calculation_details["adsorbate"] = running.pk

        self.report(f'calc_details written: {self.ctx.calculation_details}')

        return ToContext(workchains=append_(running))
    
    def postprocessing(self):
        adsorbate_post_supercell(self.inputs.mono_struct, self.inputs.bulk_struct, 
            self.ctx.calculation_parameters, self.ctx.calculation_details, self.ctx.struct_list, self.ctx.num_adsorbate)

        

