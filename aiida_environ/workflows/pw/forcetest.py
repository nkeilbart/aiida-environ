from aiida import orm
from aiida.engine import WorkChain
from aiida.plugins import CalculationFactory

PwCalculation = CalculationFactory('environ.pw')

#@calcfunction
#def interpolate(self):

class EnvPwForceTest(WorkChain):

    @classmethod
    def define(cls, spec):
       super().define(spec)
       spec.input() # input file data
       spec.outline(
           cls.run_pw_displaced,
           cls.interpolate,
       )

    def run_pw_displaced(self):
        structure = self.input.structure
        dr = 0.01
        energies, forces = {}, {}
        #PwCalculation - setup input, then displace

    def interpolate(self):
        calcForces = []
        i = 2
        while i <= len(energies)-1:
            calcForces.append(energies[f'{i}-1'] - energies[f'{i}+1']) / (2*dr))

# need to add entry points to setup.json
