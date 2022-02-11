# -*- coding: utf-8 -*-
from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain, calcfunction
from aiida.orm import Dict, Float
from aiida.plugins import WorkflowFactory
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

EnvPwBaseWorkChain = WorkflowFactory("environ.pw.base")


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
        # TODO call the base workchain instead of envpwcalculation
        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace="base",
            namespace_options={"help": "Inputs for the `EnvPwCalculation`."},
        )
        spec.input(
            "environ_vacuum",
            valid_type=Dict,
            required=False,
            help="The base parameter input for an environ simulation",
        )
        spec.input(
            "environ_solution",
            valid_type=Dict,
            required=False,
            help="The base parameter input for an environ simulation",
        )
        spec.input(
            "energy_vacuum",
            valid_type=Float,
            required=False,
            help="The vacuum energy in eV, if provided, skips the vacuum calculation",
        )
        spec.outline(
            cls.setup,
            cls.run_simulations,
            cls.post_processing,
            cls.produce_result,
        )
        spec.output("solvation_energy", valid_type=Float)

    # @classmethod
    # def get_builder_from_protocol(
    #     cls,
    #     code,
    #     structure,
    #     protocol=None,
    #     overrides=None
    # ):
    #     """Return a builder prepopulated with inputs selected according to the chosen protocol.
    #     # TODO add protocols for solvation, requires inherit ProtocolMixin

    #     :param code: the ``Code`` instance configured for the ``environ.pw`` plugin.
    #     :param structure: the ``StructureData`` instance to use.
    #     :param protocol: protocol to use, if not specified, the default will be used.
    #     :param overrides: optional dictionary of inputs to override the defaults of the protocol.
    #     """
    #     inputs = cls.get_protocol_inputs(protocol, overrides)

    #     args = (code, structure, protocol)
    #     base = EnvPwBaseWorkChain.get_builder_from_protocol(*args, overrides=inputs.get('base', None))

    #     builder = cls.get_builder()
    #     builder.base = base

    #     return builder

    def setup(self):
        from copy import deepcopy

        """context setup"""
        self.ctx.should_run_vacuum = True
        if "energy_vacuum" in self.inputs:
            # don't run a vacuum calculation
            self.ctx.should_run_vacuum = False

        self.ctx.vacuum_inputs = AttributeDict(
            self.exposed_inputs(EnvPwBaseWorkChain, namespace="base")
        )
        self.ctx.solution_inputs = AttributeDict(
            self.exposed_inputs(EnvPwBaseWorkChain, namespace="base")
        )
        environ_parameters = self.inputs.base.pw.environ_parameters.get_dict()
        if "environ_vacuum" in self.inputs:
            vacuum_overrides = self.inputs.environ_vacuum.get_dict()
        else:
            vacuum_overrides = {}
        if "environ_solution" in self.inputs:
            solution_overrides = self.inputs.environ_solution.get_dict()
        else:
            solution_overrides = {}

        self.ctx.vacuum_inputs.pw.environ_parameters = deepcopy(
            recursive_merge(environ_parameters, vacuum_overrides)
        )
        self.ctx.solution_inputs.pw.environ_parameters = deepcopy(
            recursive_merge(environ_parameters, solution_overrides)
        )

        # Set all the defaults

        self.ctx.vacuum_inputs.pw.environ_parameters.setdefault("ENVIRON", {})
        self.ctx.vacuum_inputs.pw.environ_parameters["ENVIRON"].setdefault("verbose", 0)
        self.ctx.vacuum_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "environ_thr", 1e-1
        )
        self.ctx.vacuum_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "environ_type", "vacuum"
        )
        self.ctx.vacuum_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "environ_restart", False
        )
        self.ctx.vacuum_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "env_electrostatic", True
        )

        self.ctx.vacuum_inputs.pw.environ_parameters.setdefault("ELECTROSTATIC", {})
        self.ctx.vacuum_inputs.pw.environ_parameters["ELECTROSTATIC"].setdefault(
            "solver", "direct"
        )
        self.ctx.vacuum_inputs.pw.environ_parameters["ELECTROSTATIC"].setdefault(
            "auxiliary", "none"
        )

        self.ctx.solution_inputs.pw.environ_parameters.setdefault("ENVIRON", {})
        self.ctx.solution_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "verbose", 0
        )
        self.ctx.solution_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "environ_thr", 1e-1
        )
        self.ctx.solution_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "environ_type", "water"
        )
        self.ctx.solution_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "environ_restart", False
        )
        self.ctx.solution_inputs.pw.environ_parameters["ENVIRON"].setdefault(
            "env_electrostatic", True
        )

        self.ctx.solution_inputs.pw.environ_parameters.setdefault("ELECTROSTATIC", {})
        self.ctx.solution_inputs.pw.environ_parameters["ELECTROSTATIC"].setdefault(
            "solver", "cg"
        )
        self.ctx.solution_inputs.pw.environ_parameters["ELECTROSTATIC"].setdefault(
            "auxiliary", "none"
        )

    def run_simulations(self):
        calculations = {}

        if self.ctx.should_run_vacuum:
            vacuum_inputs = prepare_process_inputs(
                EnvPwBaseWorkChain, self.ctx.vacuum_inputs
            )
            self.ctx.vacuum_wc = self.submit(EnvPwBaseWorkChain, **vacuum_inputs)
            calculations["vacuum"] = self.ctx.vacuum_wc

        solution_inputs = prepare_process_inputs(
            EnvPwBaseWorkChain, self.ctx.solution_inputs
        )
        self.ctx.solution_wc = self.submit(EnvPwBaseWorkChain, **solution_inputs)
        calculations["solution"] = self.ctx.solution_wc

        return ToContext(**calculations)

    def post_processing(self):
        # subtract energy in water calculation by energy in vacuum calculation
        if "energy_vacuum" in self.inputs:
            e_vacuum = self.inputs.energy_vacuum
        else:
            e_vacuum = self.ctx.vacuum_wc.outputs.output_parameters["energy"]

        e_solvent = self.ctx.solution_wc.outputs.output_parameters["energy"]
        self.ctx.energy_difference = subtract_energy(Float(e_solvent), Float(e_vacuum))

    def produce_result(self):
        self.out("solvation_energy", self.ctx.energy_difference)
