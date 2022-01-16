from aiida.orm.utils import load_node
from aiida.engine import calcfunction

@calcfunction
def compare_forces(pks, interpolation, order, dh):

    '''Compare DFT total force to numerical derivative dE/dx.
    
    Args:
        pks: aiida.orm.List
        interpolation: aiida.orm.Str
        order: aiida.orm.Str
        dh: aiida.orm.Float

    Returns:
        difference: list
    '''

    dft_Fs = [load_node(calc).res.total_force for calc in pks]
    fin_Fs = []
    differences = []

    n = len(pks) # number of calcs

    for i in range(n):

        ith_calc = dft_Fs[i]     # ith-calculation
        prev_calc = dft_Fs[i-1]  # preceding calculation
        next_calc = dft_Fs[i+1]  # following calculation

        ith_E = ith_calc.res.energy
        prev_E = prev_calc.res.energy
        next_E = next_calc.res.energy

        if order == 'first':

            if interpolation == 'central':
                if i > 0 and i < n-1:
                    dE = (next_E - prev_E) / dh
                    fin_Fs.append(dE)
                    differences.append(dft_Fs[i] - dE)
            elif interpolation == 'forward':
                if i < n-1:
                    dE = (next_E - ith_E) / dh
                    fin_Fs.append(dE)
                    differences.append(dft_Fs[i] - dE)
            elif interpolation == 'backward':
                if i > 0:
                    dE = (ith_E - prev_E) / dh
                    fin_Fs.append(dE)
                    differences.append(dft_Fs[i] - dE)

        elif order == 'second': 

            if interpolation == 'central':
                if i > 0 and i < n-1:
                    dE = (next_E + 2*ith_E - prev_E) / (2*dh)**2 # FIXME 2*dh needed for central implementation; dh requires half-steps -- ~2x calculations needed to compare??
                    fin_Fs.append(dE)
                    Fdiff = (dft_Fs[i+1] - dft_Fs[i-1]) - dE
                    differences.append(abs(Fdiff))

            elif interpolation == 'forward':
                if i < n-2:
                    next2_calc = load_node(pks[i+2])
                    next2_E = next2_calc.res.energy
                    dE = (next2_E - next_E + ith_E) / dh**2
                    fin_Fs.append(dE)
                    Fdiff = (dft_Fs[i+1] - dft_Fs[i]) - dE
                    differences.append(abs(Fdiff))

            elif interpolation == 'backward':
                if i > 1:
                    prev2_calc = load_node(pks[i-2])
                    prev2_E = prev2_calc.res.energy
                    dE = (ith_E - 2*prev_E + prev2_E) / dh**2
                    fin_Fs.append(dE)
                    Fdiff = (dft_Fs[i] - dft_Fs[i-1]) - dE
                    differences.append(abs(Fdiff))

    return differences # TODO return DFT Fs & numerical Fs?