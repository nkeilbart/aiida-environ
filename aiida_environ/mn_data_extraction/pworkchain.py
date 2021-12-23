from aiida.orm import List, Float, QueryBuilder, StructureData, Int, Str, Dict, nodes
from aiida.engine import ToContext, submit, append_, calcfunction, WorkChain, CalcJob
from aiida.common import AttributeDict
from aiida.plugins import WorkflowFactory
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida.orm.utils import load_node
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
import numpy as np
import time

# @calcfunction
# def square_error(y_real, y_calc):
#     return (y_real - y_calc) ** 2

# @calcfunction
# def sum(x, y):
#     return x + y

@calcfunction
def multiply(x, y):
    return x * y

@calcfunction
def subtract(x, y):
    return x - y

SolvationWorkChain = WorkflowFactory('environ.pw.solvation')

class PWorkchain(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(SolvationWorkChain, namespace='base',
            namespace_options={'help': 'Inputs for the `SolvationWorkChain`.'},
            exclude=('pw.structure', 'pw.pseudos'))
        spec.input('structure_pks', valid_type = List)
        spec.input('expt_energy_vals', valid_type = List)
        # spec.input('learning_rates', valid_type=Dict, required=False)
        spec.outline(
            # cls.setup,
            cls.simulation,
            cls.postprocessing
        )
        spec.output('MSE_Loss', valid_type = Float)
        spec.output('alpha_grad', valid_type = Float)
        spec.output('beta_grad', valid_type = Float)
        spec.output('gamma_grad', valid_type = Float)
        # spec.output('next_alpha', valid_type = Float)
        # spec.output('next_beta', valid_type = Float)
        # spec.output('next_gamma', valid_type = Float)

    # def setup(self):
        # Add logic for setting defaults for new

    def simulation(self):
        inputs = AttributeDict(self.exposed_inputs(SolvationWorkChain, namespace='base'))
        inputs.pw.environ_parameters = inputs.pw.environ_parameters.get_dict()
        inputs.pw.environ_parameters['ENVIRON'].setdefault('verbose', 1)
        qb = QueryBuilder()
        qb.append(StructureData, filters={'id': {'in': list(self.inputs.structure_pks)}})
        self.ctx.pk_calls_0 = [] # pk values for the submitted jobs or environ pw calcfunction
        self.ctx.pk_calls_1 = []
        for i, struct in enumerate(qb.all()):
            struct = struct[0]
            inputs.pw.structure = struct
            inputs.pw.pseudos = get_pseudos_from_structure(struct, 'SSSP') # 'SSSP' is pseudos library for profile 'ajay'
            inputs = prepare_process_inputs(SolvationWorkChain, inputs)
            future = self.submit(SolvationWorkChain, **inputs)
            key = f'workchain_{i}'

            self.report(f'launching SolvationWorkChain<{future.pk}> w/ Structure<{struct.pk}>')
            self.ctx.pk_calls_0.append(future.pk)
            self.to_context(workchains = append_(future))

        inputs.environ_solution = inputs.environ_solution.get_dict()
        old_alpha = inputs.pw.environ_parameters['BOUNDARY']['alpha']
        inputs.environ_solution.setdefault('BOUNDARY', {})
        inputs.environ_solution['BOUNDARY']['alpha'] = old_alpha + 1e-6
        for i, struct in enumerate(qb.all()):
            struct = struct[0]
            inputs.pw.structure = struct
            
            inputs.pw.pseudos = get_pseudos_from_structure(struct, 'SSSP') # 'SSSP' is pseudos library for profile 'ajay'
            inputs = prepare_process_inputs(SolvationWorkChain, inputs)
            future = self.submit(SolvationWorkChain, **inputs)
            key = f'workchain_{i}'

            self.report(f'launching SolvationWorkChain<{future.pk}> w/ Structure<{struct.pk}>')
            self.ctx.pk_calls_1.append(future.pk)
            self.to_context(workchains = append_(future))

    def postprocessing(self):
        #=== Hardcoded values ===#
        gamma_learning = 1e-2
        beta_learning = 1e-3
        alpha_learning = -5e-3
        #========================#
        sq_error = 0
        real_vs_0 = 0
        cnt1 = 0
        for pk, energy_real in zip(self.ctx.pk_calls_0, list(self.inputs.expt_energy_vals)):
            wc = load_node(pk)
            if wc.attributes['exit_status'] == 0:
                cnt1 += 1
                energy_calc = wc.outputs.solvation_energy.value
                sq_error += (energy_real / 23 - energy_calc) ** 2

                jobnodes = []
                for desc in wc.called_descendants:
                    if type(desc) == nodes.process.calculation.calcjob.CalcJobNode:
                        jobnodes.append(desc.pk)
                solvation = load_node(max(jobnodes))
                qm_surf = solvation.outputs.output_parameters['qm_surface'][-1]
                qm_vol = solvation.outputs.output_parameters['qm_volume'][-1]
                real_vs_0 += (energy_real / 23 - energy_calc)

        diff_1_0 = 0
        cnt2 = 0
        for pk_0, pk_1 in zip(self.ctx.pk_calls_0, self.ctx.pk_calls_1):
            wc_0 = load_node(pk_0)
            wc_1 = load_node(pk_1)
            if wc_0.attributes['exit_status'] == 0 and wc_1.attributes['exit_status'] == 0:
                cnt2 += 1
                energy_0 = wc_0.outputs.solvation_energy.value
                energy_1 = wc_1.outputs.solvation_energy.value
                diff_1_0 += (energy_1 - energy_0)

        gamma_grad = multiply(Float(real_vs_0), Float(qm_surf * gamma_learning * 2 / cnt1))
        beta_grad = multiply(Float(real_vs_0), Float(qm_vol * beta_learning * 2 / cnt1))
        alpha_grad = multiply(Float(diff_1_0), Float(alpha_learning * 1e+6))
        mse_loss = multiply(Float(sq_error), Float(1 / cnt2))

        # inputs = AttributeDict(self.exposed_inputs(SolvationWorkChain, namespace='base'))
        # environ_parameters = inputs.pw.environ_parameters.get_dict()
        # environ_solution = inputs.environ_solution.get_dict()

        # next_alpha = subtract(Float(environ_parameters['BOUNDARY']['alpha']), alpha_grad)
        # next_gamma = subtract(Float(environ_solution['ENVIRON']['env_surface_tension']), gamma_grad)
        # next_beta = subtract(Float(environ_solution['ENVIRON']['env_pressure']), beta_grad)

        self.out('MSE_Loss', mse_loss)
        # self.out('next_alpha', next_alpha)
        # self.out('next_beta', next_beta)
        # self.out('next_gamma', next_gamma)
        self.out('alpha_grad', alpha_grad)
        self.out('beta_grad', beta_grad)
        self.out('gamma_grad', gamma_grad)