from aiida.orm.utils import load_node
from aiida.engine import calcfunction

@calcfunction
def compare_forces(pks, atom, axis):

    '''Compare DFT total force to numerical derivative dE/dx.
    
    Args:
        pks: aiida.orm.List
        atom: aiida.orm.Int
        axis: aiida.orm.Int

    Returns:
        difference: list
    '''

    fin_Fs = []
    dft_Fs = []
    differences = []

    for i in range(1, len(pks)-1):

        ith = load_node(pks[i])     # ith-calculation
        prec = load_node(pks[i-1])  # preceding calculation
        fllw = load_node(pks[i+1])  # following calculation
        
        prec_coord = prec.inputs.structure.sites[atom].position[axis]
        foll_coord = fllw.inputs.structure.sites[atom].position[axis]

        dE = (fllw.res.energy - prec.res.energy) / (foll_coord - prec_coord)
        F = ith.res.total_force

        fin_Fs.append(dE)
        dft_Fs.append(F)
        differences.append(abs(F - dE))

    return differences # TODO return DFT Fs & numerical Fs?