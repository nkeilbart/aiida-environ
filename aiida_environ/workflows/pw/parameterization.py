# -*- coding: utf-8 -*-
from copy import deepcopy

from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain
from aiida.orm import Dict, Float, Int, List, Str
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_node
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

from aiida_environ.calculations.partial import calc_partial
from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain


class ParameterizationWorkChain(WorkChain):
    """WorkChain that guesses at the next set of parameters to be tuned for a specific solvent.

    The solvent is represented by a set of physical parameters and the solutes that train the solvent parameters
    are given in a list. The experimental energy values need to be provided in order for the mean squared error to
    be computed.

    The workchain calculates the solvation energy for each input structure and computes the mean squared error.

    # TODO implement a learning rate which can be given by the user
    # TODO implement a loop to fully automate the minimization algorithm
    # TODO add ability to switch between interface models, currently only the soft-sphere model is implemented
    # TODO add ProtocolMixin
    """

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace="base",
            namespace_options={"help": "Inputs for the `SolvationWorkChain`."},
            exclude=("pw.structure", "pw.pseudos"),
        )
        spec.input(
            "structure_pks",
            valid_type=List,
            help="A list of PK values for the solute structures",
        )
        spec.input(
            "expt_energy",
            valid_type=List,
            help="A list of experimental energies for optimization",
        )
        spec.input(
            "pseudo_label",
            valid_type=Str,
            help="The label for the pseudo group stored by the user",
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
        spec.outline(
            cls.setup,
            cls.run_vacuum,
            cls.run_solution,
            cls.post_processing,
            cls.produce_result,
        )
        spec.output("partials", valid_type=Dict)
        # spec.output('next_alpha', valid_type = Float)
        # spec.output('next_beta', valid_type = Float)
        # spec.output('next_gamma', valid_type = Float)

    def setup(self):
        self.ctx.nstruct = len(self.inputs.structure_pks)
        self.ctx.delta = 1e-6
        self.ctx.calculations = {}

        environ_parameters = self.inputs.base.pw.environ_parameters.get_dict()
        if "environ_vacuum" in self.inputs:
            vacuum_overrides = self.inputs.environ_vacuum.get_dict()
        else:
            vacuum_overrides = {}
        if "environ_solution" in self.inputs:
            solution_overrides = self.inputs.environ_solution.get_dict()
        else:
            solution_overrides = {}

        # force verbosity on
        vacuum_overrides["ENVIRON"]["verbose"] = 1
        solution_overrides["ENVIRON"]["verbose"] = 1

        self.ctx.vacuum_inputs = deepcopy(
            recursive_merge(environ_parameters, vacuum_overrides)
        )
        self.ctx.solution_inputs_0 = deepcopy(
            recursive_merge(environ_parameters, solution_overrides)
        )
        self.ctx.solution_inputs_1 = deepcopy(
            recursive_merge(environ_parameters, solution_overrides)
        )

        old_alpha = self.ctx.solution_inputs_1["BOUNDARY"]["alpha"]
        self.ctx.solution_inputs_1["BOUNDARY"]["alpha"] = old_alpha + self.ctx.delta

    def run_vacuum(self):
        calculations = {}

        # Loop through and compute vacuum energy
        for i, structure_pk in enumerate(self.inputs.structure_pks):
            struct = load_node(structure_pk)
            inputs = AttributeDict(
                self.exposed_inputs(EnvPwBaseWorkChain, namespace="base")
            )
            inputs.pw.structure = struct
            inputs.pw.pseudos = get_pseudos_from_structure(
                struct, self.inputs.pseudo_label.value
            )
            inputs.pw.environ_parameters = self.ctx.vacuum_inputs
            inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
            future = self.submit(EnvPwBaseWorkChain, **inputs)
            key = f"vacuum_{i}"
            self.ctx.calculations[key] = future.pk

            self.report(
                f"launching vacuum EnvPwBaseWorkChain<{future.pk}> w/ Structure<{struct.pk}>"
            )
            calculations[key] = future

        return ToContext(**calculations)

    def run_solution(self):
        calculations = {}

        # Loop through and compute solution energy for alpha = alpha_0
        for i, structure_pk in enumerate(self.inputs.structure_pks):
            struct = load_node(structure_pk)
            inputs = AttributeDict(
                self.exposed_inputs(EnvPwBaseWorkChain, namespace="base")
            )
            inputs.pw.structure = struct
            inputs.pw.pseudos = get_pseudos_from_structure(
                struct, self.inputs.pseudo_label.value
            )
            inputs.pw.environ_parameters = self.ctx.solution_inputs_0
            inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
            future = self.submit(EnvPwBaseWorkChain, **inputs)
            key = f"solution_0_{i}"
            self.ctx.calculations[key] = future.pk

            self.report(
                f"launching solution_0 EnvPwBaseWorkChain<{future.pk}> w/ Structure<{struct.pk}>"
            )
            calculations[key] = future

        # Loop through and compute solution energy for alpha = alpha_0 + d alpha
        for i, structure_pk in enumerate(self.inputs.structure_pks):
            struct = load_node(structure_pk)
            inputs = AttributeDict(
                self.exposed_inputs(EnvPwBaseWorkChain, namespace="base")
            )
            inputs.pw.structure = struct
            inputs.pw.pseudos = get_pseudos_from_structure(
                struct, self.inputs.pseudo_label.value
            )
            inputs.pw.environ_parameters = self.ctx.solution_inputs_1
            inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
            future = self.submit(EnvPwBaseWorkChain, **inputs)
            key = f"solution_1_{i}"
            self.ctx.calculations[key] = future.pk

            self.report(
                f"launching solution_1 EnvPwBaseWorkChain<{future.pk}> w/ Structure<{struct.pk}>"
            )
            calculations[key] = future

        return ToContext(**calculations)

    def post_processing(self):
        self.ctx.results = calc_partial(
            Int(self.ctx.nstruct),
            Float(self.ctx.delta),
            self.inputs.expt_energy,
            Dict(dict=self.ctx.calculations),
        )

        # inputs = AttributeDict(self.exposed_inputs(SolvationWorkChain, namespace='base'))
        # environ_parameters = inputs.pw.environ_parameters.get_dict()
        # environ_solution = inputs.environ_solution.get_dict()

        # next_alpha = subtract(Float(environ_parameters['BOUNDARY']['alpha']), alpha_grad)
        # next_gamma = subtract(Float(environ_solution['ENVIRON']['env_surface_tension']), gamma_grad)
        # next_beta = subtract(Float(environ_solution['ENVIRON']['env_pressure']), beta_grad)

    def produce_result(self):
        self.out("partials", self.ctx.results)
