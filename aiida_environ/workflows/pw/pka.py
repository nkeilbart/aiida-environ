# -*- coding: utf-8 -*-
"""
Workchain to perform pKa calculations using the Environ module
coupled with the Quantum ESPRESSO pw.x.
"""
from aiida import orm
from aiida.common import AttributeDict, exceptions
from aiida.common.lang import type_check
from aiida.engine import ToContext, WorkChain, append_, if_, while_
from aiida.plugins import WorkflowFactory, DataFactory, CalculationFactory
from aiida_quantumespresso.common.types import RelaxType
from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin
from aiida.orm import load_group, load_code, StructureData
import numpy as np

PwRelaxWorkChain = WorkflowFactory("environ.pw.relax")

def validate_inputs(inputs, _):
    """Validate the top level namespace."""
    parameters = inputs["vacuum"]["base"]["pw"]["parameters"].get_dict()

    if "relaxation_scheme" not in inputs and "calculation" not in parameters.get(
        "CONTROL", {}
    ):
        return "The parameters in `base.pw.parameters` do not specify the required key `CONTROL.calculation`."


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
            'phonopy_code',
            valid_type = orm.Code,
            help = 'Phonopy code for performing vibration calculations.'
        )
        spec.input_namespace(
            'structures', 
            valid_type = StructureData, 
            help = 'Dictionary of structures for pKa calculations.'
        )
        spec.input(
            'clean_workdir', 
            valid_type=orm.Bool, 
            default=lambda: orm.Bool(False),
            help = ('If `True`, work directories of all called calculation '
                    'will be cleaned at the end of execution.')
        )
        spec.input(
            'pseudo_family',
            valid_type = orm.Str,
            default = lambda: orm.Str('SSSP/1.1/PBE/precision'),
            help = ('Choose which pseudopotential family library to use. '
                    'Must be installed through aiida-pseudo.'
            )
        )
        spec.inputs.validator = validate_inputs
        spec.outline(
            cls.setup,
            # Optimize structures in both vacuum and solution
            cls.run_vacuum,
            cls.check_vacuum,
            cls.run_solution,
            cls.check_solution,
            # Take optimized structures and run through phonopy
            cls.run_phonopy,
            cls.check_phonopy,
            cls.postprocess_phonopy,
            cls.results,
        )
        spec.exit_code(
            403, 
            'ERROR_ENVIRON_VACUUM_CALCULATION_FAILED',
            message = 'the environ vacuum PwRelaxWorkChain failed'
        )
        spec.exit_code(
            404, 
            'ERROR_ENVIRON_SOLUTION_CALCULATION_FAILED',
            message = 'the environ solution PwRelaxWorkChain failed'
        )
        spec.exit_code(
            405,
            'PSEUDO_FAMILY_DOES_NOT_EXIST',
            message = 'pseudo family does not exist'
        )
        spec.output_namespace(
            'output_structures',
            valid_type = StructureData,
            required = False,
            help = ('Optimized structures for vacuum and solution '
                    'calculations')
        )
        spec.output(
            'pKa',
            valid_type = orm.Dict,
            required = False,
            help = ('Dictionary of results for both vacuum and solution '
                    'calculations.')
        )
        # yapf: enable

    @classmethod
    def get_builder_from_protocol(
        cls,
        code: orm.Code,
        phonopy_code: orm.Code,
        structures: dict,
        protocol: orm.Dict = None,
        overrides: orm.Dict = None,
        relax_type = RelaxType.POSITIONS,
        pseudo_family = 'SSSP/1.1/PBE/precision',
        clean_workdir: bool=True,
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

        args = (code, list(structures.values())[0], protocol)
        builder = cls.get_builder()

        vacuum = PwRelaxWorkChain.get_builder_from_protocol(
            *args, 
            relax_type=relax_type,
            **kwargs
        )
        solution = PwRelaxWorkChain.get_builder_from_protocol(
            *args, 
            relax_type=relax_type,
            **kwargs
        )

        vacuum["base"]["pw"].pop("structure", None)
        vacuum.pop("clean_workdir", None)
        solution["base"]["pw"].pop("structure", None)
        solution.pop("clean_workdir", None)        

        # Declare the environ.in file input
        environ_input = {
            'ENVIRON': {
                'env_electrostatic': True,
                'env_confine': 0.0,
                'environ_restart': False,
                'env_static_permittivity': 78.3,
                'env_pressure': -0.35,
                'env_surface_tension': 50,
                'verbose': 1,
                'environ_thr': 100
            },
            'BOUNDARY': {
                'alpha': 1.12,
                'radius_mode': 'muff',
                'solvent_mode': 'ionic',
                'deriv_method': 'lowmem'
            },
            'ELECTROSTATIC': {
                'auxiliary': 'none',
                'pbc_correction': 'parabolic',
                'pbc_dim': 0,
                'solver': 'cg',
                'tol': 1.E-10
            }
        }
        solution['base']['pw']['environ_parameters'] = orm.Dict(dict=environ_input)
        environ_input['ENVIRON']['env_static_permittivity'] = 1.0
        environ_input['ENVIRON']['env_pressure'] = 0.0
        environ_input['ENVIRON']['env_surface_tension'] = 0.0
        environ_input['ELECTROSTATIC']['solver'] = 'direct'
        vacuum['base']['pw']['environ_parameters'] = orm.Dict(dict=environ_input)  

        builder.phonopy_code = phonopy_code
        builder.vacuum = vacuum
        builder.solution = solution
        builder.structures = structures
        builder.clean_workdir = orm.Bool(clean_workdir)
        builder.pseudo_family = orm.Str(pseudo_family)

        return builder

    def setup(self):
        """Input validation and context setup."""
        self.ctx.vacuum_failed = True
        self.ctx.solution_failed = True

        # Check if pseudo family exists
        family_name = self.inputs.pseudo_family.value
        try:
            pseudo_family = load_group(family_name)
        except:
            self.report(f'failed to load pseudo family {family_name}')
            return self.exit_codes.PSEUDO_FAMILY_DOES_NOT_EXIST
        
        # Initialize results for both vacuum and solution calculations
        results = {
            'vacuum': {},
            'solution': {}
        }
        output_structures = {
            'vacuum': {},
            'solution': {}
        }
        self.ctx.results = results
        self.ctx.output_structures = output_structures

        return

    def run_vacuum(self):
        """
        Run vacuum environment simulations for all structures.
        """

        self.ctx.vacuum = AttributeDict()
        # Iterate over the list of structures and attach to the inputs.
        for key, structure in self.inputs.structures.items():
            inputs = AttributeDict(
                self.exposed_inputs(
                    PwRelaxWorkChain,
                    namespace='vacuum'
                )
            )

            inputs.base.pw.structure = structure
            pseudo_family = load_group(self.inputs.pseudo_family.value)
            inputs.base.pw.pseudos = pseudo_family.get_pseudos(
                structure=structure
            )
            inputs.base.pw.pseudo_family = self.inputs.pseudo_family

            self.ctx.results['vacuum'][key] = {}
            self.ctx.output_structures['vacuum'][key] = {}

            future = self.submit(PwRelaxWorkChain, **inputs)
            self.report(f'submitting `PwRelaxWorkChain` <PK={future.pk}>.')
            self.to_context(**{f'vacuum.{key}': future})

        return
    
    def check_vacuum(self):
        """
        Inspect output of vacuum simulations.
        """
        for key, workchain in self.ctx.vacuum.items():

            if workchain.is_failed:
                self.report(f'`PwRelaxWorkChain` failed for vacuum calculation {key}.')
                return self.exit_codes.ERROR_ENVIRON_VACUUM_CALCULATION_FAILED
            
            # Add final structure to results
            structure = workchain.outputs.output_structure
            self.ctx.output_structures['vacuum'][key]['structure'] = structure
            
        self.ctx.vacuum_failed = False

        return

    def run_solution(self):
        """
        Run solution environment simulations for all structures.
        """

        self.ctx.solution = AttributeDict()
        # Iterate over the list of structures and attach to the inputs.
        for key, structure in self.inputs.structures.items():
            inputs = AttributeDict(
                self.exposed_inputs(
                    PwRelaxWorkChain,
                    namespace='solution'
                )
            )
            inputs.base.pw.structure = structure
            pseudo_family = load_group(self.inputs.pseudo_family.value)
            inputs.base.pw.pseudos = pseudo_family.get_pseudos(
                structure=structure
            )
            inputs.base.pw.pseudo_family = self.inputs.pseudo_family

            self.ctx.results['solution'][key] = {}
            self.ctx.output_structures['solution'][key] = {}

            future = self.submit(PwRelaxWorkChain, **inputs)
            self.report(f'submitting `PwRelaxWorkChain` <PK={future.pk}>.')
            self.to_context(**{f'solution.{key}': future})

        return
    
    def check_solution(self):
        """
        Inspect output of vacuum simulations.
        """
        for key, workchain in self.ctx.solution.items():

            if workchain.is_failed:
                self.report(f'`PwRelaxWorkChain` failed for solution calculation {key}.')
                return self.exit_codes.ERROR_ENVIRON_SOLUTION_CALCULATION_FAILED
            
            # Add final structure to results
            structure = workchain.outputs.output_structure
            self.ctx.output_structures['solution'][key]['structure'] = structure
            
        self.ctx.solution_failed = False

        return
    
    def run_phonopy(self):
        """
        Take the final structures from the vacuum and solution calculations
        and run phonopy on all structures to generate displacements.
        """

        PreProcessData = DataFactory("phonopy.preprocess")
        supercell_matrix = [1,1,1]
        self.ctx.phonopy = AttributeDict()
        self.ctx.phonopy.vacuum = {}
        self.ctx.phonopy.solution = {}

        self.ctx.preprocess_data = AttributeDict()
        self.ctx.preprocess_data.vacuum = {}
        self.ctx.preprocess_data.solution = {}

        for label, structure in self.ctx.vacuum.items():
            self.ctx.phonopy.vacuum[label] = {}
            preprocess_data = PreProcessData(structure, supercell_matrix)
            supercells = preprocess_data.get_supercells_with_displacements()
            self.ctx.preprocess_data['vacuum'][label] = preprocess_data
            pseudo_family = load_group(self.inputs.pseudo_family.value)
            # Initialize inputs for each supercell and submit
            for key, supercell in supercells.items():
                inputs = AttributeDict(
                self.exposed_inputs(
                    PwRelaxWorkChain,
                    namespace='vacuum'
                    )
                )
                inputs.base.pw.parameters["CONTROL"]["calculation"] = 'scf'
                inputs.base.pw.structure = supercell
                inputs.base.pw.pseudos = pseudo_family.get_pseudos(
                    structure=supercell
                )
                inputs.base.pw.pseudo_family = self.inputs.pseudo_family

                future = self.submit(PwRelaxWorkChain, **inputs)
                self.report(f'submitting `PwRelaxWorkChain` <PK={future.pk}>.')
                self.to_context(**{f'phonopy.vacuum.{label}.{key}': future})

        for label, structure in self.ctx.solution.items():
            self.ctx.phonopy.solution[label] = {}
            preprocess_data = PreProcessData(structure, supercell_matrix)
            supercells = preprocess_data.get_supercells_with_displacements()
            self.ctx.preprocess_data['solution'][label] = preprocess_data
            pseudo_family = load_group(self.inputs.pseudo_family.value)
            # Initialize inputs for each supercell and submit
            for key, supercell in supercells.items():
                inputs = AttributeDict(
                self.exposed_inputs(
                    PwRelaxWorkChain,
                    namespace='solution'
                    )
                )
                inputs.base.pw.parameters["CONTROL"]["calculation"] = 'scf'
                inputs.base.pw.structure = supercell
                inputs.base.pw.pseudos = pseudo_family.get_pseudos(
                    structure=supercell
                )
                inputs.base.pw.pseudo_family = self.inputs.pseudo_family

                future = self.submit(PwRelaxWorkChain, **inputs)
                self.report(f'submitting `PwRelaxWorkChain` <PK={future.pk}>.')
                self.to_context(**{f'phonopy.solution.{label}.{key}': future})      

        return
    
    def check_phonopy(self):
        """
        Check the results of all phonopy calculations. Gather the information
        as needed to do the postprocess step.
        """
        dict_of_forces = AttributeDict()
        dict_of_forces.vacuum = {}
        dict_of_forces.solution = {}

        phonopy_pk = []
        for label, supercells in self.ctx.phonopy.vacuum.items():
            dict_of_forces['vacuum'][label] = {}
            for key, supercell in supercells.items():
                if supercell.is_failed:
                    phonopy_pk.append(supercell.pk)
                else:
                    force_name = f'forces_{key.split("_")[-1]}'
                    forces = supercell.outputs.output_trajectory.get_array('forces')
                    dict_of_forces['vacuum'][label][force_name] = forces

        for label, supercells in self.ctx.phonopy.solution.items():
            dict_of_forces['solution'][label] = {}
            for key, supercell in supercells.items():
                if supercell.is_failed:
                    phonopy_pk.append(supercell.pk)
                else:
                    force_name = f'forces_{key.split("_")[-1]}'
                    forces = supercell.outputs.output_trajectory.get_array('forces')
                    dict_of_forces['solution'][label][force_name] = forces

        if phonopy_pk:
            self.report(f'`pKaWorkChain failed at phonopy calculations {" ".join(phonopy_pk)}')
        else:
            self.report('phonopy calculations finished')

        self.ctx.forces = dict_of_forces

        return
    
    def postprocess_phonopy(self):

        PhonopyData = DataFactory("phonopy.phonopy")
        PhonopyCalculation = CalculationFactory("phonopy.phonopy")
        phonopy_code = self.inputs.phonopy_code
        phonopy_parameters = AttributeDict(dictionary={
            'EIGENVECTORS': True,
            'DIM': [1, 1, 1],
            'MESH': [1, 1, 1],
            'GAMMA_CENTER': True,
            'TPROP': True,
            'TMAX': 298.15,
            'TMIN': 298.15,
            'CUTOFF_FREQUENCY': 10,
            'FC_SYMMETRY': True
        })

        phonopy_calcs = AttributeDict(dictionary={
            'vacuum': {},
            'solution': {}
        })

        for label, preprocess_data in self.ctx.preprocess_data.vacuum.items():

            preprocess_data = self.ctx.preprocess_data['vacuum'][label]
            phonopy_data =  PhonopyData(preprocess_data=preprocess_data)

            dict_of_forces = self.ctx.forces.vacuum[label]
            phonopy_data.set_forces(dict_of_forces=dict_of_forces)

            builder = PhonopyCalculation.get_builder()
            builder.code = phonopy_code
            builder.phonopy_data = phonopy_data
            builder.parameters = phonopy_parameters

            future = self.submit(builder)
            self.report(f'submitting `PhonopyCalculation` <PK={future.pk}>.')
            self.to_context(**{f'phonopy_calcs.vacuum.{label}': future})  

        for label, preprocess_data in self.ctx.preprocess_data.solution.items():

            preprocess_data = self.ctx.preprocess_data['solution'][label]
            phonopy_data =  PhonopyData(preprocess_data=preprocess_data)

            dict_of_forces = self.ctx.forces.solution[label]
            phonopy_data.set_forces(dict_of_forces=dict_of_forces)

            builder = PhonopyCalculation.get_builder()
            builder.code = phonopy_code
            builder.phonopy_data = phonopy_data
            builder.parameters = phonopy_parameters

            future = self.submit(builder)
            self.report(f'submitting `PhonopyCalculation` <PK={future.pk}>.')
            self.to_context(**{f'phonopy_calcs.solution.{label}': future}) 

        return

    def results(self):
        """Attach the output parameters and structure of the last workchain to the outputs."""
        if not self.ctx.vacuum_failed and not self.ctx.solution_failed:
            self.report(f"pka workchain completed")

        results = self.ctx.results
        output_structures = self.ctx.output_structures

        for e, v in self.ctx.vacuum.items():
            output = v.outputs.output_parameters.get_dict()
            results['vacuum'][e]['output'] = output
        for e, s in self.ctx.solution.items():
            output = s.outputs.output_parameters.get_dict()
            results['solution'][e]['output'] = output

        results = orm.Dict(dict=results)
        results.store()

        self.out("pKa", results)
        self.out("output_structures", output_structures)

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