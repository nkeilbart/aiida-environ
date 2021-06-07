from math import gcd, reduce
import numpy as np

from aiida.engine import calcfunction

from aiida_environ.utils.charge import get_charge_range

def get_nstruct(struct):
    atoms = {}
    for site in struct.sites:
        if site.kind_name not in atoms:
            atoms[site.kind_name] = 1
        else:
            atoms[site.kind_name] += 1
    n = reduce(gcd, list(atoms.values()))
    return n

@calcfunction
def adsorbate_post_supercell(mono_struct, bulk_struct, c_params, c_details, struct_list, num_adsorbate):

    charge_max = c_params['charge_max']
    charge_inc = c_params['charge_increment']
    charge_range = get_charge_range(charge_max, charge_inc)

    n_mono = get_nstruct(mono_struct)
    n_bulk = get_nstruct(bulk_struct)

    bulk_node = c_details["bulk"]
    g_bulk = bulk_node.outputs.output_parameters["energy"] * n_mono / n_bulk
    bulk_adsorbate_node = c_details["adsorbate"]
    g_bulk_adsorbate = bulk_adsorbate_node.outputs.output_parameters["energy"]
    # TODO: this needs to be generalized for any adsorbate..
    g_bulk_adsorbate /= 2

    j_ip = np.zeros((len(struct_list), len(charge_range), ), dtype=float)

    for i, (na, structure_pk) in enumerate(zip(num_adsorbate, struct_list)):
        for j, charge_amt in enumerate(charge_range):
            # want to get the Delta(G_DFT) for each adsorbate configuration and each charge
            adsorbate_node = c_details[charge_amt][structure_pk]
            g_ads = adsorbate_node.outputs.output_parameters["energy"]
            f_ads = adsorbate_node.outputs.output_parameters["fermi_energy"]
            f_ads += adsorbate_node.outputs.output_parameters["fermi_energy_correction"]
            dg_ads = g_ads - g_bulk
            ne_ads = adsorbate_node.inputs.parameters["SYSTEM"]["tot_charge"]
            # TODO: consider another charge of the adsorbate that isn't just '1'
            ne_ads = 1 * na
            # units in eV so..
            j_ip[i, j] = dg_ads - (g_bulk_adsorbate * na) + ne_ads * f_ads