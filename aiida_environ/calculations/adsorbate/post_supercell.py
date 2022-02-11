# -*- coding: utf-8 -*-
from functools import reduce
from math import gcd

import numpy as np
from aiida.engine import calcfunction
from aiida.orm import Dict, List, StructureData
from aiida.orm.utils import load_node
from scipy import interpolate

from aiida_environ.utils.charge import get_charge_range


def get_nstruct(struct: StructureData):
    """gets the greatest common divisor between atom types

    Args:
        struct (StructureData): the atomic structure object

    Returns:
        int: effectively the number of repeats in the cell
    """
    atoms = {}
    for site in struct.sites:
        if site.kind_name not in atoms:
            atoms[site.kind_name] = 1
        else:
            atoms[site.kind_name] += 1
    n = reduce(gcd, list(atoms.values()))
    return n


@calcfunction
def adsorbate_post_supercell(
    mono_struct: StructureData,
    bulk_struct: StructureData,
    c_params: Dict,
    c_details: Dict,
    struct_list: List,
    num_adsorbate: List,
):

    charge_max = c_params["charge_max"]
    charge_inc = c_params["charge_increment"]
    charge_range = get_charge_range(charge_max, charge_inc)

    # we want the size ratio between the monolayer and the bulk material
    size_mono = get_nstruct(mono_struct)
    size_bulk = get_nstruct(bulk_struct)

    # array sizes
    n_struct = len(struct_list) + 1
    n_charge = len(charge_range)

    # bulk values used for reference
    bulk_node = load_node(c_details["bulk"])
    free_energy_bulk = (
        bulk_node.outputs.output_parameters["energy"] * size_mono / size_bulk
    )
    bulk_adsorbate_node = load_node(c_details["adsorbate"])
    free_energy_adsorbate = bulk_adsorbate_node.outputs.output_parameters["energy"]
    # TODO: this needs to be generalized for any adsorbate..
    free_energy_adsorbate /= 2

    # delta free energy (the difference in energy between monolayer and bulk)
    delta_free_energy_adsorption = np.zeros(
        (
            n_struct,
            n_charge,
        ),
        dtype=float,
    )
    # fermi energy (the QE fermi energy plus the Environ potential shift correction)
    fermi_energy_adsorption = np.zeros(
        (
            n_struct,
            n_charge,
        ),
        dtype=float,
    )

    for j, charge_amt in enumerate(charge_range):
        # the 0% coverage results
        adsorbate_node = load_node(c_details[charge_amt]["mono"])
        g_ads = adsorbate_node.outputs.output_parameters["energy"]
        fermi_energy_adsorption[0, j] = adsorbate_node.outputs.output_parameters[
            "fermi_energy"
        ]
        fermi_energy_adsorption[0, j] += adsorbate_node.outputs.output_parameters[
            "fermi_energy_correction"
        ]
        delta_free_energy_adsorption[0, j] = g_ads - free_energy_bulk

    for i, structure_pk in enumerate(struct_list):
        for j, charge_amt in enumerate(charge_range):
            # n% coverage results (>0, <=100)
            adsorbate_node = load_node(c_details[charge_amt][structure_pk])
            g_ads = adsorbate_node.outputs.output_parameters["energy"]
            fermi_energy_adsorption[
                i + 1, j
            ] = adsorbate_node.outputs.output_parameters["fermi_energy"]
            fermi_energy_adsorption[
                i + 1, j
            ] += adsorbate_node.outputs.output_parameters["fermi_energy_correction"]
            delta_free_energy_adsorption[i + 1, j] = g_ads - free_energy_bulk
            ne_ads = adsorbate_node.inputs.parameters["SYSTEM"]["tot_charge"]

    j_ip = np.zeros(
        (n_struct, n_charge),
        dtype=float,
    )

    for i in range(len(struct_list) + 1):
        for j in range(len(charge_range)):
            # TODO: consider another charge of the adsorbate that isn't just '1'
            ne_ads = 1 * na
            # units in eV so..
            j_ip[i, j] = (
                delta_free_energy_adsorption[i, j]
                - (g_bulk_adsorbate * na)
                + ne_ads * fermi_energy_adsorption
            )

    # now that we have all the input data, perform analysis

    # fermi range needs to be calculated
    fermi_min = np.amin(fermi_energy_adsorption, axis=1)
    fermi_max = np.amax(fermi_energy_adsorption, axis=1)
    sparse_inc = 0.2
    fine_inc = 0.01

    f_ensemble = []
    j_ensemble = []
    e_ensemble = []

    for i, na in enumerate(num_adsorbate):
        # interpolate for the potential
        fermi_range = np.arange(fermi_min[i], fermi_max[i], sparse_inc)
        j_min = []  # the minimum j value for a specific potential increment
        f_min = []  # the potential that results in the min j value
        for j, fermi in fermi_range:
            j_value = []
            for k, charge_amt in enumerate(charge_range):
                j_value.append(delta_free_energy_adsorption[i, k] - charge_amt * fermi)
            j_min.append(min(j_value))
            f_min.append(fermi_range[np.where(fermi)[0][0]])

        # now interpolate to get a fine mapping
        itp_func = interpolate.interp1d(
            f_min, j_min, kind="quadratic", bounds_error=False
        )
        fermi_range = np.arange(min(f_min), max(f_min), fine_inc)
        j_fine = itp_func(fermi_range)

        f_ensemble.append(fermi_range)
        j_ensemble.append(j_fine)

        # interpolate for the pH, assume T = 300K
        boltzmann = 2.58519e-2  # in eV
        ph = 7 * 59.5369  # neutral pH of 7, multiply by RT

        if na > 0 and na < max(num_adsorbate):
            # fractional coverage
            fcov = na / max(num_adsorbate)
            ecorr = (
                8 * (fcov * np.log(fcov) + (1 - fcov) * np.log(1 - fcov)) * boltzmann
            )
            surf_e = (0.5 / na) * (
                j_ensemble
                - (na * 2 * free_energy_adsorbate)
                + (2 * na * (ph - 4.44))
                + ecorr
            )
        else:
            surf_e = None
        e_ensemble.append(surf_e)

    # choose the best potential range
    upper = float("inf")  # the minimum upper bound in f_ensemble
    lower = float("-inf")  # the maximum lower bound in f_ensemble
    highest = float("-inf")
    lowest = float("inf")
    for i, f in enumerate(f_ensemble):
        lower = max(lower, np.min(f))
        upper = min(upper, np.max(f))
        highest = max(highest, np.max(f))
        lowest = min(lowest, np.min(f))

    # many strategies are viable here.. we decide to take the full range available and
    # the reduced range if it exists. The reduced range is the data that is generated by
    # interpolation only, and the full data includes extrapolated data. Note that it's possible
    # that the ranges don't overlap at all, and the only available data is extrapolated data..
    # in which case it might be nice to store the ranges in the database for further querying
    if upper - lower > 0.0:
        intra_range = np.arange(lower, upper, fine_inc)
    else:
        intra_range = None
    extra_range = np.arange(lowest, highest, fine_inc)

    j_intra = []
    j_extra = []
    for f, j, e in zip(f_ensemble, j_ensemble, e_ensemble):
        if e is None:
            itp_func = interpolate.interp1d(f, j, kind="quadratic", bounds_error=False)
        else:
            itp_func = interpolate.interp1d(f, e, kind="quadratic", bounds_error=False)
        if intra_range is None:
            j_intra.append(None)
        else:
            j_intra.append(itp_func(intra_range))
        j_extra.append(itp_func(extra_range))

    # TODO: want to output these j_intra, j_extra values for plotting
