# -*- coding: utf-8 -*-
"""
Workchain to perform pKa calculations using the Environ module
coupled with the Quantum ESPRESSO pw.x.
"""
from aiida import orm
from aiida.common import AttributeDict, exceptions
from aiida.common.lang import type_check
from aiida.engine import ToContext, WorkChain, append_, if_, while_
from aiida.plugins import CalculationFactory, WorkflowFactory
from aiida_quantumespresso.common.types import RelaxType
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin

PwRelaxWorkChain = WorkflowFactory("environ.pw.relax")

def validate_inputs(inputs, _):
    """Validate the top level namespace."""
    parameters = inputs["base"]["pw"]["parameters"].get_dict()

    if "relaxation_scheme" not in inputs and "calculation" not in parameters.get(
        "CONTROL", {}
    ):
        return "The parameters in `base.pw.parameters` do not specify the required key `CONTROL.calculation`."


def validate_final_scf(value, _):
    """Validate the final scf input."""
    if isinstance(value, orm.Bool) and value:
        import warnings

        from aiida.common.warnings import AiidaDeprecationWarning

        warnings.warn(
            "this input is deprecated and will be removed. If you want to run a final scf, specify the inputs that "
            "should be used in the `base_final_scf` namespace.",
            AiidaDeprecationWarning,
        )


def validate_relaxation_scheme(value, _):
    """Validate the relaxation scheme input."""
    if value:
        import warnings

        from aiida.common.warnings import AiidaDeprecationWarning

        warnings.warn(
            "the `relaxation_scheme` input is deprecated and will be removed. Use the `get_builder_from_protocol` "
            "instead to obtain a prepopulated builder using the `RelaxType` enum.",
            AiidaDeprecationWarning,
        )

class pKaWorkChain(ProtocolMixin, WorkChain):
    """
    Workchain to perform pKa calculations using Quantum ESPRESSO pw.x.
    """

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)
        spec.expose_inputs(
            PwRelaxWorkChain, 
            namespace = 'vacuum',
            exclude = ('clean_workdir', 'pw.structure', 'pw.parent_folder'),
            namespace_options = {
                'help': ('Inputs for the `PwBaseWorkChain` for the main '
                         'relax loop.')
            }
        )
        spec.expose_inputs(
            PwRelaxWorkChain, 
            namespace = 'solution',
            exclude = ('clean_workdir', 'pw.structure', 'pw.parent_folder'),
            namespace_options = {
                'help': ('Inputs for the `PwBaseWorkChain` for the main '
                         'relax loop.')
            }
        )
        spec.input(
            'structures', 
            valid_type = orm.List, 
            help = 'List of structures for pKa calculations.'
        )
        spec.input(
            'clean_workdir', 
            valid_type=orm.Bool, 
            default=lambda: orm.Bool(False),
            help = ('If `True`, work directories of all called calculation '
                    'will be cleaned at the end of execution.')
        )
        spec.inputs.validator = validate_inputs
        spec.outline(
            cls.setup,
            cls.run_vacuum,
            cls.check_vacuum,
            cls.run_solution,
            cls.check_solution,
            cls.results,
        )
        spec.exit_code(
            401, 
            'ERROR_SUB_PROCESS_FAILED_RELAX',
            message = 'the relax PwBaseWorkChain sub process failed'
        )
        spec.exit_code(
            402, 
            'ERROR_SUB_PROCESS_FAILED_FINAL_SCF',
            message = 'the final scf PwBaseWorkChain sub process failed'
        )
        spec.expose_outputs(
            PwRelaxWorkChain, 
            exclude = ('output_structure',)
        )
        spec.output(
            'output_structures', 
            valid_type = orm.StructureData, 
            required = False,
            help = 'The successfully relaxed structure.'
        )
        # yapf: enable

    @classmethod
    def get_builder_from_protocol(
        cls,
        code,
        structures,
        protocol=None,
        overrides=None,
        relax_type=RelaxType.POSITIONS_CELL,
        **kwargs,
    ):
        """
        Return a builder prepopulated with inputs selected according to the chosen protocol.

        :param code: the ``Code`` instance configured for the ``quantumespresso.pw`` plugin.
        :param structure: the ``StructureData`` instance to use.
        :param protocol: protocol to use, if not specified, the default will be used.
        :param overrides: optional dictionary of inputs to override the defaults of the protocol.
        :param relax_type: the relax type to use: should be a value of the enum ``common.types.RelaxType``.
        :param kwargs: additional keyword arguments that will be passed to the ``get_builder_from_protocol`` of all the
            sub processes that are called by this workchain.
        :return: a process builder instance with all inputs defined ready for launch.
        """
        type_check(relax_type, RelaxType)

        args = (code, structures[0], protocol)
        inputs = cls.get_protocol_inputs(protocol, overrides)
        builder = cls.get_builder()

        base = PwRelaxWorkChain.get_builder_from_protocol(
            *args, overrides=inputs.get("base", None), **kwargs
        )

        base["pw"].pop("structure", None)
        base.pop("clean_workdir", None)

        # Quantum ESPRESSO currently only supports optimization of the volume for simple cubic systems. It requires
        # to set `ibrav=1` or the code will except.
        if relax_type in (RelaxType.VOLUME, RelaxType.POSITIONS_VOLUME):
            raise ValueError(f"relax type `{relax_type} is not yet supported.")

        if relax_type in (RelaxType.VOLUME, RelaxType.SHAPE, RelaxType.CELL):
            base.pw.settings = orm.Dict(
                dict=pKaWorkChain._fix_atomic_positions(
                    structure, base.pw.settings
                )
            )

        if relax_type is RelaxType.NONE:
            base.pw.parameters["CONTROL"]["calculation"] = "scf"
            base.pw.parameters.delete_attribute("CELL")

        elif relax_type is RelaxType.POSITIONS:
            base.pw.parameters["CONTROL"]["calculation"] = "relax"
            base.pw.parameters.delete_attribute("CELL")
        else:
            base.pw.parameters["CONTROL"]["calculation"] = "vc-relax"

        if relax_type in (RelaxType.VOLUME, RelaxType.POSITIONS_VOLUME):
            base.pw.parameters["CELL"]["cell_dofree"] = "volume"

        if relax_type in (RelaxType.SHAPE, RelaxType.POSITIONS_SHAPE):
            base.pw.parameters["CELL"]["cell_dofree"] = "shape"

        if relax_type in (RelaxType.CELL, RelaxType.POSITIONS_CELL):
            base.pw.parameters["CELL"]["cell_dofree"] = "all"

        builder.base = base
        builder.structures = structures
        builder.clean_workdir = orm.Bool(inputs["clean_workdir"])

        return builder

    def setup(self):
        """Input validation and context setup."""
        self.ctx.current_number_of_bands = None
        self.ctx.current_cell_volume = None
        self.ctx.is_converged = False
        self.ctx.iteration = 0

        self.ctx.relax_inputs = AttributeDict(
            self.exposed_inputs(PwRelaxWorkChain, namespace="base")
        )
        self.ctx.relax_inputs.pw.parameters = (
            self.ctx.relax_inputs.pw.parameters.get_dict()
        )

        self.ctx.relax_inputs.pw.parameters.setdefault("CONTROL", {})
        self.ctx.relax_inputs.pw.parameters["CONTROL"]["restart_mode"] = "from_scratch"

        # Adjust the inputs for the chosen relaxation scheme
        if "relaxation_scheme" in self.inputs:
            if self.inputs.relaxation_scheme.value in ("relax", "vc-relax"):
                self.ctx.relax_inputs.pw.parameters["CONTROL"][
                    "calculation"
                ] = self.inputs.relaxation_scheme.value
            else:
                raise ValueError("unsupported value for the `relaxation_scheme` input.")

        # Set the meta_convergence and add it to the context
        self.ctx.meta_convergence = self.inputs.meta_convergence.value
        volume_cannot_change = (
            self.ctx.relax_inputs.pw.parameters["CONTROL"]["calculation"]
            in ("scf", "relax")
            or self.ctx.relax_inputs.pw.parameters.get("CELL", {}).get(
                "cell_dofree", None
            )
            == "shape"
        )
        if self.ctx.meta_convergence and volume_cannot_change:
            self.report(
                "No change in volume possible for the provided base input parameters. Meta convergence is turned off."
            )
            self.ctx.meta_convergence = False

        # Add the final scf inputs to the context if a final scf should be run
        if self.inputs.final_scf and "base_final_scf" in self.inputs:
            raise ValueError(
                "cannot specify `final_scf=True` and `base_final_scf` at the same time."
            )
        elif self.inputs.final_scf:
            self.ctx.final_scf_inputs = AttributeDict(
                self.exposed_inputs(PwBaseWorkChain, namespace="base")
            )
        elif "base_final_scf" in self.inputs:
            self.ctx.final_scf_inputs = AttributeDict(
                self.exposed_inputs(PwBaseWorkChain, namespace="base_final_scf")
            )

        if "final_scf_inputs" in self.ctx:
            if self.ctx.relax_inputs.pw.parameters["CONTROL"]["calculation"] == "scf":
                self.report(
                    "Work chain will not run final SCF when `calculation` is set to `scf` for the relaxation "
                    "`PwBaseWorkChain`."
                )
                self.ctx.pop("final_scf_inputs")

            else:
                self.ctx.final_scf_inputs.pw.parameters = (
                    self.ctx.final_scf_inputs.pw.parameters.get_dict()
                )

                self.ctx.final_scf_inputs.pw.parameters.setdefault("CONTROL", {})
                self.ctx.final_scf_inputs.pw.parameters["CONTROL"][
                    "calculation"
                ] = "scf"
                self.ctx.final_scf_inputs.pw.parameters["CONTROL"][
                    "restart_mode"
                ] = "from_scratch"
                self.ctx.final_scf_inputs.pw.parameters.pop("CELL", None)
                self.ctx.final_scf_inputs.metadata.call_link_label = "final_scf"

    def run_vacuum(self):
        """
        Run vacuum environment simulations for all structures.
        """

        self.ctx.vacuum = AttributeDict()
        # Iterate over the list of structures and attach to the inputs.
        for e, structure in enumerate(self.inputs.structures):
            inputs = AttributeDict(
                self.exposed_inputs(
                    PwRelaxWorkChain,
                    namespace='vacuum'
                )
            )
            inputs.pw.structure = structure
            future = self.submit(PwRelaxWorkChain, **inputs)
            self.report(f'submitting `PwRelaxWorkChain` <PK={future.pk}>.')
            self.to_context(**{f'vacuum.{e}': future})

        return
    
    def check_vacuum(self):
        """
        Inspect output of vacuum simulations.
        """
        for key, workchain in self.ctx.vacuum.items():

            if workchain.is_failed:
                self.report(f'`PwRelaxWorkChain` failed for vacuum calculation {key}.')
                return self.exit_codes.ERROR_SUB_PROCESS_FAILED_RELAX

        return

    def run_solution(self):
        """
        Run solution environment simulations for all structures.
        """

        self.ctx.solution = AttributeDict()
        # Iterate over the list of structures and attach to the inputs.
        for e, structure in enumerate(self.inputs.structures):
            inputs = AttributeDict(
                self.exposed_inputs(
                    PwRelaxWorkChain,
                    namespace='solution'
                )
            )
            inputs.pw.structure = structure
            future = self.submit(PwRelaxWorkChain, **inputs)
            self.report(f'submitting `PwRelaxWorkChain` <PK={future.pk}>.')
            self.to_context(**{f'solution.{e}': future})

        return
    
    def check_solution(self):
        """
        Inspect output of vacuum simulations.
        """
        for key, workchain in self.ctx.solution.items():

            if workchain.is_failed:
                self.report(f'`PwRelaxWorkChain` failed for solution calculation {key}.')
                return self.exit_codes.ERROR_SUB_PROCESS_FAILED_RELAX

        return

    def results(self):
        """Attach the output parameters and structure of the last workchain to the outputs."""
        if (
            self.ctx.is_converged
            and self.ctx.iteration <= self.inputs.max_meta_convergence_iterations.value
        ):
            self.report(f"workchain completed after {self.ctx.iteration} iterations")
        else:
            self.report("maximum number of meta convergence iterations exceeded")

        # Get the latest relax workchain and pass the outputs
        final_relax_workchain = self.ctx.workchains[-1]

        if self.inputs.base.pw.parameters["CONTROL"]["calculation"] != "scf":
            self.out("output_structure", final_relax_workchain.outputs.output_structure)

        try:
            self.out_many(self.exposed_outputs(self.ctx.workchain_scf, PwBaseWorkChain))
        except AttributeError:
            self.out_many(self.exposed_outputs(final_relax_workchain, PwBaseWorkChain))

    def on_terminated(self):
        """Clean the working directories of all child calculations if `clean_workdir=True` in the inputs."""
        super().on_terminated()

        if self.inputs.clean_workdir.value is False:
            self.report("remote folders will not be cleaned")
            return

        cleaned_calcs = []

        for called_descendant in self.node.called_descendants:
            if isinstance(called_descendant, orm.CalcJobNode):
                try:
                    called_descendant.outputs.remote_folder._clean()  # pylint: disable=protected-access
                    cleaned_calcs.append(called_descendant.pk)
                except (IOError, OSError, KeyError):
                    pass

        if cleaned_calcs:
            self.report(
                f"cleaned remote folders of calculations: {' '.join(map(str, cleaned_calcs))}"
            )

    @staticmethod
    def _fix_atomic_positions(structure, settings):
        """Fix the atomic positions, by setting the `FIXED_COORDS` key in the `settings` input node."""
        if settings is not None:
            settings = settings.get_dict()
        else:
            settings = {}

        settings["FIXED_COORDS"] = [[True, True, True]] * len(structure.sites)

        return settings
