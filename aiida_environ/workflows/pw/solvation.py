from aiida.engine import WorkChain, ToContext, append_, calcfunction
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.orm import StructureData, Bool, Str, Int, Float, Code
from aiida.common import AttributeDict, exceptions
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

EnvPwCalculation = CalculationFactory('environ.pw')

@calcfunction
def subtract_energy(x, y):
    return x - y

class PwSolvationWorkChain(WorkChain):

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(EnvPwCalculation, namespace='pw',
            namespace_options={'help': 'Inputs for the `EnvPwCalculation`.'})
        spec.outline(
            cls.setup,
            cls.vacuum,
            cls.solution,
            cls.post_processing,
            cls.produce_result
        )
        spec.output('solvation_energy', valid_type = Float)

    def setup(self):
        pass
    
    def vacuum(self):
        inputs = AttributeDict(self.exposed_inputs(EnvPwCalculation, namespace='pw'))
        
        inputs.environ_parameters = inputs.environ_parameters.get_dict()

        inputs.environ_parameters.setdefault('ENVIRON', {
            'verbose': 0,
            'environ_thr': 1e-1,
            'environ_type': 'vacuum',
            'env_electrostatic': True
        })
        inputs.environ_parameters.setdefault('ELECTROSTATIC', {
            # 'pbc_correction': 'parabolic',
            # 'pbc_dim': 0,
            # 'tol': 1e-11,
            # 'mix': 0.6,
            'solver': 'direct',
            'auxiliary': 'none'
        })

        # If one of the nested `PwBaseWorkChains` changed the number of bands, apply it here
        # if self.ctx.current_number_of_bands is not None:
        #     inputs.pw.parameters.setdefault('SYSTEM', {})['nbnd'] = self.ctx.current_number_of_bands

        # # Set the `CALL` link label
        # inputs.metadata.call_link_label = 'iteration_{:02d}'.format(self.ctx.iteration)

        inputs = prepare_process_inputs(EnvPwCalculation, inputs)
        running = self.submit(EnvPwCalculation, **inputs)
        self.report('launching EnvPwCalculation<{}>'.format(running.pk))
        return ToContext(workchains = append_(running))
    
    def solution(self):
        inputs = AttributeDict(self.exposed_inputs(EnvPwCalculation, namespace='pw'))

        inputs.environ_parameters = inputs.environ_parameters.get_dict()

        inputs.environ_parameters.setdefault('ENVIRON', {
            'verbose': 0,
            'environ_thr': 1e-1,
            'environ_type': 'water',
            'env_electrostatic': True
        })
        inputs.environ_parameters.setdefault('ELECTROSTATIC', {
            # 'pbc_correction': 'parabolic',
            # 'pbc_dim': 0,
            # 'tol': 1e-11,
            # 'mix': 0.6,
            'solver': 'cg',
            'auxiliary': 'none'
        })

        inputs = prepare_process_inputs(EnvPwCalculation, inputs)
        running = self.submit(EnvPwCalculation, **inputs)
        self.report('launching EnvPwCalculation<{}>'.format(running.pk))
        return ToContext(workchains = append_(running))
    
    def post_processing(self): 
        # subtract energy in water calculation by energy in vacuum calculation
        workchain_vacuum = self.ctx.workchains[0]
        workchain_solution = self.ctx.workchains[1]
        e_solvent = workchain_vacuum.outputs.output_parameters.get_dict()['energy']
        e_vacuum = workchain_solution.outputs.output_parameters.get_dict()['energy']
        self.ctx.energy_difference = subtract_energy(Float(e_solvent), Float(e_vacuum))
    
    def produce_result(self):
        self.out('solvation_energy', self.ctx.energy_difference)
        
