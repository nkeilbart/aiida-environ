# -*- coding: utf-8 -*-
from aiida import orm
from aiida.common.folders import Folder
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.engine import CalcJob, CalcJobProcessSpec

from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.calculations import BasePwCpInputGenerator, _lowercase_dict, _uppercase_dict
from aiida_quantumespresso.utils.convert import convert_input_to_namelist_entry

class EnvPwCalculation(PwCalculation):
    @classmethod
    def define(cls, spec: CalcJobProcessSpec) -> None:
        """Define the process specification."""
        # yapf: disable
        super().define(spec)
        spec.input('environ_parameters', valid_type=orm.Dict,
            help='The input parameters that are to be used to construct the input file.')
        spec.output('output_environ_parameters', valid_type=orm.Dict,
            help='The `output_environ_parameters` output node of the successful calculation.')

    def prepare_for_submission(self, folder: Folder) -> CalcInfo:
        calcinfo = BasePwCpInputGenerator.prepare_for_submission(self, folder)
        calcinfo.cmdline_params.append('--environ')
        if 'settings' in self.inputs:
            settings = _uppercase_dict(self.inputs.settings.get_dict(), dict_name='settings')
        else:
            settings = {}
        input_filecontent = self._generate_environinputdata(self.inputs.parameters, self.inputs.structure, settings)

        # write the environ input file (name is fixed)
        with folder.open('environ.in', 'w') as handle:
            handle.write(input_filecontent)

        return calcinfo

    @classmethod
    def _generate_environinputdata(cls, parameters, structure, settings):  # pylint: disable=invalid-name 
        # NOTE currently, `settings` does nothing but the plan is to have a user-friendly `parameter` equivalence
        # which has a lower precedence than `parameters`. That is, the user can set parameters via `settings`, and
        # tweak them more individually in `parameters`
             
        # The following input_params declaration is taken from the aiida-qe (3.1.0)  
        # I put the first-level keys as uppercase (i.e., namelist and card names)
        # and the second-level keys as lowercase
        # (deeper levels are unchanged)
        input_params = _uppercase_dict(parameters.get_dict(), dict_name='parameters')
        input_params = {k: _lowercase_dict(v, dict_name=k) for k, v in input_params.items()}

        # set namelists_toprint explicitly, environ has 3 standard namelists which are expected
        inputfile = ''
        namelists_toprint = ['ENVIRON', 'BOUNDARY', 'ELECTROSTATIC']

        # To create a mapping from the species to an incremental fortran 1-based index
        # we use the alphabetical order as in the inputdata generation
        kind_names = sorted([kind.name for kind in structure.kinds])
        mapping_species = {kind_name: (index + 1) for index, kind_name in enumerate(kind_names)}
        
        for namelist_name in namelists_toprint:
            inputfile += '&{0}\n'.format(namelist_name)
            # namelist content; set to {} if not present, so that we leave an empty namelist
            namelist = input_params.pop(namelist_name, {})
            for key, value in sorted(namelist.items()):
                inputfile += convert_input_to_namelist_entry(key, value, mapping=mapping_species)
            inputfile += '/\n'

        # TODO add cards

        return inputfile