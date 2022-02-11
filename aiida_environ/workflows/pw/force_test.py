# -*- coding: utf-8 -*-
import random

from aiida.engine import WorkChain
from aiida.orm import Dict, List, StructureData

from aiida_environ.calculations.finite import calculate_finite_differences

from aiida_environ.workflows.pw.base import EnvPwBaseWorkChain


def _get_default_settings() -> Dict:
    """Returns default Dict if input test_settings is None."""

    defaults = Dict(
        dict={
            "diff_type": "central",
            "diff_order": "first",  # center worked
            "atom_to_perturb": 1,
            "n_steps": 1,
            "step_sizes": [0.01, 0.00, 0.00],
        }
    )

    return defaults


class EnvPwForceTestWorkChain(WorkChain):
    """
    WorkChain to evaluate EnvPwBaseWorkChain forces against finite difference forces.

    # TODO consider rewriting the run_test in line with other workflows (so setup with
    # AttributeDict, and store calcs consistently)

    Inputs:
    EnvPwBaseWorkChain inputs:  aiida.orm.Dict
    structure:                  aiida.orm.StructureData
    test_settings:              aiida.orm.Dict

    Outputs:
    results:                    aiida.orm.Dict
    """

    types = ("forward", "backward", "central")  # finite difference type tuple
    orders = ("first", "second")  # finite difference order tuple
    axes = ("x", "y", "z")  # axis tuple

    @classmethod
    def define(cls, spec):
        """I/O specifications & WorkChain outline."""

        super().define(spec)

        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace="base",
            namespace_options={"help": "Inputs for the `FiniteForcesWorkChain`."},
            exclude=("pw.structure",),
        )
        spec.input("structure", valid_type=StructureData)
        spec.input(
            "test_settings",
            valid_type=Dict,
            default=lambda: _get_default_settings(),
            help="Force test settings to increment atom_to_perturb by dr based on step_sizes [dx, dy, dz] and evaluate finite differences for n-steps",
        )
        spec.output("results", valid_type=Dict)

        spec.outline(
            cls.setup,
            cls.run_test,
            cls.get_results,
        )

    def setup(self):
        """Validates inputs and initializes needed attributes."""

        natoms = len(self.inputs.structure.sites)  # nat for random
        wild = random.randint(1, natoms)  # random index

        # set default settings for missing keys
        settings_dict = self.inputs.test_settings.get_dict()
        settings_dict.setdefault("diff_type", "forward")
        settings_dict.setdefault("diff_order", "first")
        settings_dict.setdefault("atom_to_perturb", wild)
        settings_dict.setdefault("n_steps", 5)
        settings_dict.setdefault("step_sizes", [0.1, 0.0, 0.0])

        # validate inputs
        self._validate_diff_type()
        self._validate_diff_order()
        self._validate_atom_to_perturb(natoms)
        self._validate_n_steps(settings_dict["n_steps"])
        self._validate_step_sizes()

        self.inputs.test_settings = Dict(dict=settings_dict)

    def run_test(self):
        """Calculates energy and total force for selected atom at initial position and perturbed positions."""

        # local variable block
        diff_order = self.inputs.test_settings["diff_order"]
        diff_type = self.inputs.test_settings["diff_type"]
        steps = self.inputs.test_settings["step_sizes"]
        n = (
            self.inputs.test_settings["n_steps"] + 1
        )  # initial position + n-perturbations
        prefix = f"atom{self.atom}"

        # context variable block
        self.ctx.cell = self.inputs.structure.cell
        self.ctx.edge = self.inputs.structure.cell_lengths[self.atom]
        self.ctx.sites = self.inputs.structure.sites
        self.ctx.initial_position = self.ctx.sites[self.atom].position

        # central difference requires half-step increments
        if diff_type == "central" and diff_order == "first":
            n *= 2
            step = sum([(dh / 2) ** 2 for dh in steps]) ** 0.5
        else:
            step = sum([dh**2 for dh in steps]) ** 0.5

        # submit calculations
        for i in range(n):
            chain_name = f"{prefix}.{self.ctx.axstr}.{i}"
            inputs = self._prepare_inputs(i, i * step)
            env_chain = self.submit(EnvPwBaseWorkChain, **inputs)
            self.to_context(**{chain_name: env_chain})

        # collect the WorkChains
        self.ctx.environ_chain_list = []
        for k in range(n):
            name = f"{prefix}.{self.ctx.axstr}.{k}"
            self.ctx.environ_chain_list.append(self.ctx[name].pk)

    def get_results(self):

        """
        Calculates finite differences and returns results Dict for comparison.

        Initial position:   energy & total force
        Environ energies:   DFT energies for finite differences
        Environ forces:     DFT total forces for comparison
        Delta:              DFT forces v. finite difference forces
        """

        results = calculate_finite_differences(
            List(list=self.ctx.environ_chain_list), self.inputs.test_settings
        )

        self.out("results", results)

    def _prepare_inputs(self, i: int, dr: float) -> dict:
        """Returns dictionary of inputs ready for Process submission."""

        if i == 0:
            which = "Initial"
        else:
            which = "Perturbed"

        inputs = {
            "pw": {
                "code": self.inputs.base.pw.code,
                "pseudos": self.inputs.base.pw.pseudos,
                "parameters": self.inputs.base.pw.parameters,
                "environ_parameters": self.inputs.base.pw.environ_parameters,
                "metadata": {
                    "options": {
                        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 4}
                    }
                },
            },
            "metadata": {
                "description": f"{which} structure | Atom {self.atom+1} d{self.ctx.axstr} = {dr:.2f}",
            },
            "kpoints": self.inputs.base.kpoints,
        }

        if i == 0:
            inputs["pw"]["structure"] = self.inputs.structure
        else:
            inputs["pw"]["structure"] = self._perturb_atom(
                i=i, steps=self.inputs.test_settings["step_sizes"]
            )

        return inputs

    def _perturb_atom(self, i: int, steps: list) -> StructureData:
        """Returns StructureData with updated position."""

        new_position = [0.0, 0.0, 0.0]

        # update position tuple
        for j in range(3):

            if steps[j] != 0.0:

                new_position[j] = self.ctx.initial_position[j] + i * steps[j]

                if (self.ctx.edge - new_position[j]) > 0.001:
                    continue
                else:
                    raise Exception(
                        "\nNew atom_to_perturb position appears to be outside cell bounds. Stopping."
                    )

            else:
                new_position[j] = self.ctx.initial_position[j]

        new_structure = StructureData(cell=self.ctx.cell)  # NEW STRUCTURE HAS

        # TODO index existing StructureData for one-to-one Site replacement? or use array?
        for k in range(len(self.ctx.sites)):

            if k == self.atom:
                new_structure.append_atom(
                    position=new_position, symbols=self.ctx.sites[k].kind_name
                )

            else:
                new_structure.append_atom(
                    position=self.ctx.sites[k].position,
                    symbols=self.ctx.sites[k].kind_name,
                )

        return new_structure

    def _validate_diff_type(self):
        """Validate finite difference type input."""

        type_str = self.inputs.test_settings["diff_type"]

        # type validation
        if not isinstance(type_str, str):
            raise Exception("\ndiff_type must be 'forward', 'backward', or 'central'")

        # string validation
        if type_str in self.types:
            self.inputs.test_settings.diff_type = type_str
        else:
            raise Exception(f"\n{type_str} is not valid.")

    def _validate_diff_order(self):
        """Validates finite difference order input."""

        ord_str = self.inputs.test_settings["diff_order"]

        # type validation
        if not isinstance(ord_str, str):
            raise Exception("\ndiff_order must be 'first' or 'second'")

        if ord_str in self.orders:
            self.inputs.test_settings.diff_order = ord_str
        else:
            raise Exception(f"{ord_str} is not valid")

    def _validate_step_sizes(self):
        """Validates step size inputs."""

        steplist = self.inputs.test_settings["step_sizes"]

        # type validation
        if not isinstance(steplist, list):
            raise Exception("\nstep_sizes must be a list of 3 floats")

        # length validation
        if len(steplist) != 3:
            raise Exception("\nAxis tuple must have 3 elements: [dx, dy, dz]")

        # element type validation
        for dh in steplist:
            if not isinstance(dh, float):
                raise Exception("\nStep list may only contain float values")

        # direction validation
        if steplist.count(0.0) == 2:
            for step in steplist:
                if step != 0.0:
                    direction = steplist.index(step)
            self.ctx.axstr = self.axes[direction]
        elif steplist.count(0.0) == 3:  # set default for garbage input
            raise Exception("\nStep size in every direction is 0.0")
        else:
            self.ctx.axstr = "r"

    def _validate_atom_to_perturb(self, nat):
        """Validates atom index input."""

        atom = self.inputs.test_settings["atom_to_perturb"]

        # type validation
        if not isinstance(atom, int):
            raise Exception("\natom_to_perturb must be an integer")

        # magnitude validation
        if atom < 0 or atom > nat:
            raise Exception(
                "\nAtom index must be greater than zero and less than number of atoms."
            )

        self.atom = atom - 1

    def _validate_n_steps(self, n):
        """Validates total number of steps input."""

        # type validation
        if not isinstance(n, int):
            raise Exception("\nn_steps must be an int")

        # magnitude validation
        diff_order = self.inputs.test_settings["diff_order"]
        if diff_order == "second" and n < 2:
            raise Exception(
                "\nMininum 2 steps required for second-order forward/backward finite differences."
            )
