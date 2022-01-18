from aiida.orm.utils import load_node
from aiida.orm import List, Float, Str
from aiida.engine import calcfunction

@calcfunction
def compare_forces(pks: List, dh: Float, type: Str, order: Str) -> list:

    '''Compare DFT total force to numerical derivative dE/dx.
    
    Args:
        pks:        aiida.orm.List
        dr:         aiida.orm.Float
        type:       aiida.orm.Str
        order:      aiida.orm.Str

    Returns:
        differences: list

    '''

    dft_Fs = [load_node(calc).res.total_force for calc in pks]
    fin_Fs = []
    differences = []

    if type == 'central':
        n = 2 * len(pks) # half & whole step calcs
    else:
        n = len(pks)

    for i in range(n):

        if type == 'central' and i > 0 and i % 2 == 0:

            prev_calc = dft_Fs[i-1]  # preceding calculation
            next_calc = dft_Fs[i+1]  # following calculation

            prev_E = prev_calc.res.energy
            next_E = next_calc.res.energy

            if order == 'first':

                dE = (next_E - prev_E) / dh
                fin_Fs.append(dE)
                differences.append(abs(dft_Fs[i] - dE))
            
            else:

                ith_calc = dft_Fs[i]     # ith-calculation
                ith_E = ith_calc.res.energy

                dE = (next_E + 2*ith_E - prev_E) / dh**2
                fin_Fs.append(dE)
                Fdiff = (dft_Fs[i+1] - dft_Fs[i-1]) - dE
                differences.append(abs(Fdiff))

        elif type == 'forward':

            ith_calc = dft_Fs[i]     # ith-calculation
            next_calc = dft_Fs[i+1]  # following calculation

            if order == 'first' and i < n-1:

                dE = (next_E - ith_E) / dh
                fin_Fs.append(dE)
                differences.append(abs(dft_Fs[i+1] - dE))

            elif order == 'second' and i < n-2:
                
                next2_calc = load_node(pks[i+2])
                next2_E = next2_calc.res.energy
                
                dE = (next2_E - next_E + ith_E) / dh**2
                fin_Fs.append(dE)
                Fdiff = (dft_Fs[i+1] - dft_Fs[i]) - dE
                differences.append(abs(Fdiff))

        else:

            ith_calc = dft_Fs[i]     # ith-calculation
            prev_calc = dft_Fs[i-1]  # preceding calculation

            if order == 'first' and  i > 0:
                dE = (ith_E - prev_E) / dh
                fin_Fs.append(dE)
                differences.append(abs(dft_Fs[i] - dE))

            elif order == 'second' and i > 1:

                prev2_calc = load_node(pks[i-2])
                prev2_E = prev2_calc.res.energy

                dE = (ith_E - 2*prev_E + prev2_E) / dh**2
                fin_Fs.append(dE)
                Fdiff = (dft_Fs[i] - dft_Fs[i-1]) - dE
                differences.append(abs(Fdiff))

    return differences # TODO return DFT Fs & numerical Fs?