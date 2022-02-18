# -*- coding: utf-8 -*-
from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain
from aiida.orm import List, Str, StructureData
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.orm.utils import load_node
from aiida.plugins import WorkflowFactory
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

from aiida_environ.calculations.adsorbate.gen_multitype import adsorbate_gen_multitype

EnvPwBaseWorkChain = WorkflowFactory("environ.pw.base")


class AdsorbateGraphConfiguration(WorkChain):
    """WorkChain that generates simulations for maximally connected adsorbate configurations.

    User submits a list of coordinates for the sites, `adsorbate_sites` of length `n` where `n`
    is the number of sites, that can be classified into symmetry groups. `site_index` is a list
    of length `n` that indexes the sites into groups. `possible_adsorbates` is a list of strings
    of length `s` that describe each possible adsorbate. If there are `g` groups, then `adsorbate_index`
    is a list of length `g` (outer) by `s` (inner) that describes the maximum number of adsorbate
    type that is allowed in each type of site.

    Currently adsorbates can only be single atomic species defined by strings. Ideally these would be
    replaced by `StructureData`

    Example:
        adsorbate_sites = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        site_index = [0, 1]
        possible_adsorbates = ['O', 'H']
        adsorbate_index = [[1, 1], [1, 1]]

    # TODO post processing needs machine learning
    # TODO add more functionality for different adsorbates
    """

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(
            EnvPwBaseWorkChain,
            namespace="base",
            exclude=("clean_workdir", "pw.structure", "pw.pseudos", "pw.parent_folder"),
            namespace_options={"help": "Inputs for the `PwBaseWorkChain`."},
        )
        spec.input("adsorbate_sites", valid_type=List)
        spec.input("site_index", valid_type=List)
        spec.input("possible_adsorbates", valid_type=List)
        spec.input("adsorbate_index", valid_type=List)
        spec.input("structure", valid_type=StructureData)
        spec.input(
            "pseudo_label",
            valid_type=Str,
            help="The label for the pseudo group stored by the user",
        )
        spec.outline(cls.setup, cls.selection, cls.simulate, cls.postprocessing)

    def setup(self):
        self.ctx.struct_list = []

    def selection(self):
        self.ctx.struct_list = adsorbate_gen_multitype(
            self.inputs.site_index,
            self.inputs.possible_adsorbates,
            self.inputs.adsorbate_index,
            self.inputs.structure,
            self.inputs.adsorbate_sites,
        )

    def simulate(self):
        calculations = {}

        for structure_pk in self.ctx.struct_list:
            inputs = AttributeDict(
                self.exposed_inputs(EnvPwBaseWorkChain, namespace="base")
            )
            structure = load_node(structure_pk)
            self.report(f"{structure}")
            inputs.pw.structure = structure
            inputs.pw.pseudos = get_pseudos_from_structure(
                structure, self.inputs.pseudo_label.value
            )

            inputs = prepare_process_inputs(EnvPwBaseWorkChain, inputs)
            future = self.submit(EnvPwBaseWorkChain, **inputs)
            calculations[structure_pk] = future

            self.report(f"launching PwBaseWorkChain<{future.pk}>")

        return ToContext(**calculations)

    def postprocessing(self):
        pass
