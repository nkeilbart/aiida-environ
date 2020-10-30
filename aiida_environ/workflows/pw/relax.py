# -*- coding: utf-8 -*-
"""Workchain to relax a structure using Quantum ESPRESSO pw.x."""
from aiida import orm
from aiida.common import AttributeDict, exceptions
from aiida.engine import WorkChain, ToContext, if_, while_, append_
from aiida.plugins import CalculationFactory, WorkflowFactory

from aiida_quantumespresso.utils.mapping import prepare_process_inputs

PwCalculation = CalculationFactory('quantumespresso.pw')
PwBaseWorkChain = WorkflowFactory('quantumespresso.pw.base')


class PwRelaxWorkChain(WorkChain):
    """Workchain to calculate the solvation energy using pw.x with the Environ plugin"""

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        # yapf: disable
        super().define(spec)
        spec.expose_inputs(PwBaseWorkChain, namespace='base',
            exclude=('clean_workdir', 'pw.structure', 'pw.parent_folder'),
            namespace_options={'help': 'Inputs for the `PwBaseWorkChain`.'})
        