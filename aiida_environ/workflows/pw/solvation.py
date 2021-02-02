from aiida.engine import WorkChain, ToContext, append_, calcfunction
from aiida.plugins import CalculationFactory
from aiida.orm import Float, Dict
from aiida.common import AttributeDict
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_environ.utils.merge import recursive_update_dict

EnvPwCalculation = CalculationFactory('environ.pw')

@calcfunction
def subtract_energy(x, y):
    return x - y

class PwSolvationWorkChain(WorkChain):
    """WorkChain to compute the solvation energy for a given structure using Quantum ESPRESSO pw.x + ENVIRON

    Expects one of two possible inputs by the user.
    1) An environ-parameter dictionary as per a regular environ calculation
    2) An environ-parameter dictionary with shared variables and one/two dictionaries for custom vacuum/solution
    input.
    """

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(EnvPwCalculation, namespace='pw',
            namespace_options={'help': 'Inputs for the `EnvPwCalculation`.'})
        spec.input('environ_vacuum', valid_type=Dict, required=False, help='The input for a vacuum scf simulation')
        spec.input('environ_solution', valid_type=Dict, required=False, help='The input for a solution scf simulation')
        spec.outline(
            cls.setup,
            cls.vacuum,
            cls.solution,
            cls.post_processing,
            cls.produce_result,
        )
        spec.output('solvation_energy', valid_type = Float)

    def setup(self):
        pass
    
    def vacuum(self):
        inputs = AttributeDict(self.exposed_inputs(EnvPwCalculation, namespace='pw'))
        
        inputs.environ_parameters = inputs.environ_parameters.get_dict()

        # If a custom `environ_vacuum` dict exists, copy its values over here
        if 'environ_vacuum' in self.inputs:
            recursive_update_dict(inputs.environ_parameters, self.inputs.environ_vacuum.get_dict())

        inputs.environ_parameters.setdefault('ENVIRON', {})
        inputs.environ_parameters['ENVIRON'].setdefault('verbose', 0)
        inputs.environ_parameters['ENVIRON'].setdefault('environ_thr', 1e-1)
        inputs.environ_parameters['ENVIRON'].setdefault('environ_type', 'vacuum')
        inputs.environ_parameters['ENVIRON'].setdefault('environ_restart', False)
        inputs.environ_parameters['ENVIRON'].setdefault('env_electrostatic', True)

        inputs.environ_parameters.setdefault('ELECTROSTATIC', {})
        inputs.environ_parameters['ELECTROSTATIC'].setdefault('solver', 'direct')
        inputs.environ_parameters['ELECTROSTATIC'].setdefault('auxiliary', 'none')

        inputs = prepare_process_inputs(EnvPwCalculation, inputs)
        running = self.submit(EnvPwCalculation, **inputs)

        self.report('launching EnvPwCalculation<{}>'.format(running.pk))

        return ToContext(workchains = append_(running))
    
    def solution(self):
        inputs = AttributeDict(self.exposed_inputs(EnvPwCalculation, namespace='pw'))

        inputs.environ_parameters = inputs.environ_parameters.get_dict()

        # If a custom `environ_solution` dict exists, copy its values over here
        if 'environ_solution' in self.inputs:
            recursive_update_dict(inputs.environ_parameters, self.inputs.environ_solution.get_dict())

        inputs.environ_parameters.setdefault('ENVIRON', {})
        inputs.environ_parameters['ENVIRON'].setdefault('verbose', 0)
        inputs.environ_parameters['ENVIRON'].setdefault('environ_thr', 1e-1)
        inputs.environ_parameters['ENVIRON'].setdefault('environ_type', 'water')
        inputs.environ_parameters['ENVIRON'].setdefault('environ_restart', False)
        inputs.environ_parameters['ENVIRON'].setdefault('env_electrostatic', True)

        inputs.environ_parameters.setdefault('ELECTROSTATIC', {})
        inputs.environ_parameters['ELECTROSTATIC'].setdefault('solver', 'cg')
        inputs.environ_parameters['ELECTROSTATIC'].setdefault('auxiliary', 'none')

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
        self.ctx.energy_difference = subtract_energy(Float(e_vacuum), Float(e_solvent))
    
    def produce_result(self):
        self.out('solvation_energy', self.ctx.energy_difference)
        
