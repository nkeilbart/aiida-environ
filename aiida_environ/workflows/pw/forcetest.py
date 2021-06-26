import random
import numpy as np
from pandas import DataFrame
from datetime import datetime, deltatime
from aiida.orm.utils import load_node
from aiida.engine import run # change to submit

PwCalculation = CalculationFactory('quantumespresso.pw') # str to be: 'environ.pw'
builder.metadata.label = 'pw scf force test'
builder.metadata.description = 'finite difference force test'

def find_pwscf_calcs():

    '''finds previous pwscf calcs to test, using i/o query -- working'''

    qb = QueryBuilder()
    qb.append(
        PwCalculation, # find pw process nodes
        tag='calculation',
        filters={
            'attributes.process_state': 'finished', # completed jobs only
            'attributes.exit_status': 0, # error free jobs only
            'ctime': {'>': datetime.now() - timedelta(days=7)} # recent jobs only - 1 week
        }
    )
    qb.append(
        Dict, # find pw parameter nodes
        with_outgoing='calculation',
        filters={'attributes.CONTROL.calculation': 'scf'} # scf jobs only
    )
    pks, nats = [], []
    for process in qb.all():
        calc = process[0]
        pks.append(calc.pk)
        nats.append( len(calc.inputs.structure.attributes['sites']) )
    DataFrame(data={'PK': pks, 'nat': nats}) # display legibly
    return

def run_pwscf(id):

    '''runs pwscf with a displaced atom in a cell -- in progress'''

    calc = load_node(pk)
    traj = calc.outputs.output_trajectory
    posarray = traj.get_array('positions')[0]
    index = random.randint(0, len(calc.inputs.structure.attributes['sites']) # random atom index
    position = posarray[index] # atom position
    cellmax = calc.inputs.structure.cell_lengths[0] # max x-length

    dx = 0.01
    energies = [calc.res.energy] # add last pwscf total energy
    forces = [calc.res.total_force] # add last pwscf total force
    for i in range(5):
        position[0] = position[0] + dx # translate atom
        if (cellmax - position[0]) > 0.001: # keep particle within cell
            posarray[index] = position # update array
            builder = PwCalculation.get_builder()
            builder.structure = posarray
            builder.pseudos = calc.inputs.pseudos
            builder.kpoints = calc.inputs.kpoints
            builder.parameters = calc.inputs.parameters
            tprnfr = parameters['CONTROL']['tprnfor']
            if tprnfr not True: parameters['CONTROL']['tprnfor'] = True
            testcalc = run(builder) # submit new pwscf
            energies.append(testcalc.res.energy) # add new energy
            forces.append(testcalc.res.total_force) # add new force
        else:
            break
            print('New atom position is outside cell bounds')
    builder.metadata.dry_run = True
    builder.metadata.store_provenance = False
    return energies, forces

def main():
    
    '''compares finite difference forces with dft forces -- in progress'''

    find_pwscf_calcs()
    pk = input('Select a calculation for testing (Enter a PK): ')
    pwenergies, pwforces = run_test(pk)
    finforces = ['-']
    for i in range(2, len(pwenergies) - 1):
         finforces.append(pwenergies[f'{i}-1'] - pwenergies[f'{i}+1']) / (2*dr))

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
