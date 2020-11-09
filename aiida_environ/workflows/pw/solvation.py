from aiida.engine import WorkChain, ToContext, append_
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida.orm import StructureData, Bool, Str, Int, Float
from aiida.common import AttributeDict, exceptions
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

EnvPwCalculation = CalculationFactory('environ.pw')
EnvPwBaseWorkChain = WorkflowFactory('environ.pw.base')

class PwSolvationWorkChain(WorkChain):

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(EnvPwBaseWorkChain, namespace='base',
            exclude=('clean_workdir', 'pw.parent_folder'),
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'})
        spec.input('clean_workdir', valid_type=Bool, default=lambda: Bool(False),
            help='If `True`, work directories of all called calculation will be cleaned at the end of execution.')
        spec.outline(
            cls.setup,
            cls.vacuum,
            cls.solution,
            cls.post_processing
        )
        spec.output('solvation_energy', valid_type = Float)

    def setup(self):
        pass
    
    def vacuum(self):
        inputs = AttributeDict(self.exposed_inputs(EnvPwBaseWorkChain, namespace='base'))
        
        inputs.pw.parameters = inputs.pw.parameters.get_dict()

        # Create parameter dictionaries
        inputs.pw.parameters.setdefault('CONTROL', {
            'calculation': 'scf', # Also test with calculation relax
            'restart_mode': 'from_scratch',
            'tprnfor': True
        })
        """ # Include this when calc is relax
        inputs.pw.parameters.setdefault('IONS', {
            'ion_dynamics': 'bfgs'
        })
        """
        inputs.pw.environ_parameters = inputs.pw.environ_parameters.get_dict()

        inputs.pw.environ_parameters.setdefault('ENVIRON', {
            'verbose': 0,
            'environ_thr': 1e-1,
            'environ_type': 'vacuum',
            'env_electrostatic': True
        })
        inputs.pw.environ_parameters.setdefault('ELECTROSTATIC', {
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

        inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
        running = self.submit(EnvPwCalculation, **inputs)
        self.report('launching EnvPwBaseWorkChain<{}>'.format(running.pk))
        return ToContext(workchains = append_(running))
    
    def solution(self):
        pass
    
    def post_processing(self): 
        # subtract energy in water calculation by energy in vacuum calculation
        pass
