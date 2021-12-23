from aiida.orm import Dict, StructureData, Group
import pandas as pd
import aiida
import bz2
import numpy as np
import pdb


aiida.load_profile('ajay')
def solute_structure(solute_row, cell_padding): # cell_padding on each side (4-5 Angstroms)
    elements = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og']
    filename = 'all_solutes/' + solute_row['FileHandle'] + '.xyz.bz2'
    f = bz2.open(filename, 'r')
    atoms = []
    positions = []
    for i, line in enumerate(f):
        if i > 2:
            vals = line.split()
            atoms.append(elements[int(vals[0]) - 1])
            coords = [float(i) for i in vals[1:]]
            positions.append(coords)
    positions = np.array(positions)
    dims = np.array(2 * cell_padding + np.max(positions, axis=0) - np.min(positions, axis=0))
    cell = np.diag(dims)
    s = StructureData(cell=cell)
    for atom, coords in zip(atoms, positions):
        s.append_atom(position=coords, symbols=atom)
    s.label = solute_row['FileHandle'] + '.xyz'
    return s

df = pd.read_csv('Minnesota_Solvation_Database.csv')
solvent_group = Group(label='solvent group')
solute_group = Group(label='solute group')
solvent_group.store()
solute_group.store()
lf = df[['Solvent', 'eps', 'alpha', 'beta', 'gamma']].groupby('Solvent').mean()

for i, row in lf.iterrows():
    solvent = {
        'eps': row['eps'],
        'alpha': row['alpha'],
        'beta': row['beta'],
        'gamma': row['gamma']
    }
    solvent_dict = Dict(dict=solvent)
    solvent_dict.label = row.name
    solvent_dict.store()
    solvent_group.add_nodes(solvent_dict)
    # print(solvent_dict.label)

    for i, solute in df[df['Solvent'] == row.name].iterrows():
        struct = solute_structure(solute, cell_padding=4.5)
        struct.label = solute['FileHandle']
        struct.store()

        solute_d = {
            'solvent': solvent_dict.pk, # PK value for the solvent dictionary entry
            'solute': struct.pk, # PK value for the structure entry
            'deltagsolv': solute['DeltaGsolv'],
            'totalarea': solute['TotalArea']
        }
        solute_dict = Dict(dict=solute_d)
        solute_dict.store()
        solute_group.add_nodes(solute_dict)