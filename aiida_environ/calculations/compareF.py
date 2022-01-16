from aiida.orm.utils import load_node
from aiida.engine import calcfunction

@calcfunction
def compare_forces(interpolation, pks, atom, axis):

    '''Compare DFT total force to numerical derivative dE/dx.
    
    Args:
        difftype: aiida.orm.Str
        pks: aiida.orm.List
        atom: aiida.orm.Int
        axis: aiida.orm.Int

    Returns:
        difference: list
    '''

    dft_Fs = []
    fin_Fs = []
    differences = []

    for i in range(len(pks)):

        ith = load_node(pks[i])     # ith-calculation
        prec = load_node(pks[i-1])  # preceding calculation
        fllw = load_node(pks[i+1])  # following calculation
        
        ith_coord = prec.inputs.structure.sites[atom].position[axis]
        prec_coord = prec.inputs.structure.sites[atom].position[axis]
        foll_coord = fllw.inputs.structure.sites[atom].position[axis]

        if interpolation == 'central':
            if i > 0 and i < len(pks)-1: dE = (fllw.res.energy - prec.res.energy) / (foll_coord - prec_coord)
        elif interpolation == 'forward':
            if i < len(pks)-1: dE = (fllw.res.energy - ith.res.energy) / (foll_coord - ith_coord)
        elif interpolation == 'backward':
            if i > 0: dE = (ith.res.energy - prec.res.energy) / (ith_coord - prec_coord)

        F = ith.res.total_force

        fin_Fs.append(dE)
        dft_Fs.append(F)
        differences.append(abs(F - dE))

        # TODO ADD HIGHER ORDER DIFFERENTIATION

    return differences # TODO return DFT Fs & numerical Fs?