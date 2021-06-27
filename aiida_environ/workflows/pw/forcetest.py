
import time
import random
import numpy as np
from pandas import DataFrame
from datetime import datetime, timedelta
from aiida.orm.utils import load_node
from aiida.engine import submit

PwCalculation = CalculationFactory('quantumespresso.pw') # str to be: 'environ.pw'

def find_pwscf_calcs():

    '''finds previous pwscf calcs to test, using i/o query -- working'''

    qb = QueryBuilder()
    qb.append(
        Dict,
        tag='parameters',
        filters={
            'attributes.CONTROL.calculation': 'scf',
            'attributes.CONTROL.tprnfor': True,
        }
    )
    qb.append(
        PwCalculation, # find pw process nodes
        with_incoming='parameters',
        filters={
            'attributes.process_state': 'finished', # completed jobs only
            'attributes.exit_status': 0, # error free jobs only
            'ctime': {'>': datetime.now() - timedelta(days=7)} # recent jobs only - 1 week
        }
    )
    pks, nats = [], []
    for process in qb.all():
        calc = process[0]
        pks.append(calc.pk)
        nats.append( len(calc.inputs.structure.sites) )
    print('\nPWscf calculations run in the last week')
    print( DataFrame(data={'PK': pks, 'nat': nats}) ) # display legibly
    return

def run_test(dx, id):

    '''runs pwscf with a displaced atom in a cell -- working'''
    
    pks = [id]
    energies = [] # add last pwscf total energy
    forces = [] # add last pwscf total force
    for i in range(5):
        if i == 0:
            calc = load_node(id)
        else:
            calc = load_node(testcalc.pk)
        energies.append(calc.res.energy) # add new energy
        forces.append(calc.res.total_force) # add new force
        ucell = calc.inputs.structure.cell
        sites = calc.inputs.structure.sites
        nat = len(sites)
        if i == 0:
            index = random.randint(0, nat-1) # random atom index
        position = sites[index].position # atom position
        cellmax = calc.inputs.structure.cell_lengths[0] # max x-length
        testpos = (position[0] + dx,) + position[1:] # translate atom
        if (cellmax - position[0]) > 0.001: # keep particle within cell
            sites[index].position = testpos # update array
            builder = PwCalculation.get_builder()
            builder.metadata.label = 'pw scf force test'
            builder.metadata.description = 'finite difference force test'
            builder.metadata.options.resources = {'num_machines': 1, 'num_mpiprocs_per_machine': 2}
            builder.metadata.dry_run = False
            builder.metadata.store_provenance = True
            builder.code = calc.inputs.code
            builder.pseudos = calc.inputs.pseudos
            builder.kpoints = calc.inputs.kpoints
            builder.parameters = calc.inputs.parameters
            builder.settings = calc.inputs.settings # KPOINTS gamma
            StructureData = DataFactory('structure')
            configuration = StructureData(cell=ucell)
            for i in range(nat):
                configuration.append_atom(position=sites[i].position, symbols=sites[i].kind_name)
            builder.structure = configuration
            testcalc = submit(builder) # submit new pwscf
            print()
            while testcalc.is_finished_ok != True:
                if testcalc.is_failed == True:
                    print(f'\nProcess failed: {testcalc.exit_status}\n')
                    quit()
                elif testcalc.is_excepted == True:
                    print('\nAn error occurred\n')
                    quit()
                print(testcalc.pk, '\t', testcalc.process_state)
                time.sleep(5)
        else:
            print('New atom position may be outside cell bounds')
            quit()
        pks.append(testcalc.pk)
        energies.append(calc.res.energy)
        forces.append(calc.res.total_force)
    print('\nTest completed\n')
    return pks, energies, forces

def main():
    
    '''compares finite difference forces with dft forces -- debugging'''

    find_pwscf_calcs()
    dx = 0.01
    pk = input('\nSelect a previous calculation for testing (Enter a PK): ')
    jobs, pwenergies, pwforces = run_test(dx, pk)
    finforces = ['-']
    for i in range(2, len(pwenergies) - 1):
         finforces.append( (pwenergies[i-1] - pwenergies[i+1]) / (2*dx) )
    finforces.append('-')
    print( DataFrame( \
        data={'PK': jobs, 'dft E': pwenergies, 'dft F': pwforces, 'fin F': finforces}) ) # display legibly

main()

'''backend implementation -- future development'''
#class EnvPwForceTest(WorkChain):
#
#    @classmethod
#    def define(cls, spec):
#       super().define(spec)
#       spec.input() # input file data
#       spec.outline(
#           cls.run_pw_displaced,
#        cls.interpolate,
#       )
#
#    def run_pw_displaced(self):
#        structure = self.input.structure
#        dr = 0.01
#        energies, forces = {}, {}
#        #PwCalculation - setup input, then displace
#
#    def interpolate(self):
#        calcForces = []
#        i = 2
#        while i <= len(energies)-1:
#            calcForces.append(energies[f'{i}-1'] - energies[f'{i}+1']) / (2*dr))
