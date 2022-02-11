# -*- coding: utf-8 -*-
from aiida.engine import calcfunction
from aiida.orm import Bool, Dict, List, load_node


def _setup(pks, dh, environ=True):
    """Returns initial position data and initializes global variables."""

    global N
    global STEP
    global SCALARS
    global DERIVATIVES
    global SECOND_DERIVATIVES

    N = len(pks)
    STEP = dh
    SECOND_DERIVATIVES = []

    # TODO would like to use base workchain output, but energy, force precision is slightly different
    # WorkChain.outputs.output_trajectory.get_array('energy')[0]
    # WorkChain.outputs.output_trajectory.get_array('total_force')[0]

    if environ:

        calcs = [load_node(pk).called_descendants[-1] for pk in pks]
        SCALARS = [calc.res.energy for calc in calcs]
        DERIVATIVES = [calc.res.total_force for calc in calcs]

        return {"Energy": SCALARS[0], "Total force": DERIVATIVES[0]}

    SCALARS = [load_node(pk) for pk in pks]

    return SCALARS[0]


def _calculate_first_order_difference(two_scalars: tuple, one_derivative: float):
    """Returns first-order finite difference & compares to DFT force."""

    dE = (two_scalars[1] - two_scalars[0]) / STEP
    return dE, abs(dE - one_derivative)


def _calculate_second_order_difference(
    three_scalars: tuple, two_derivatives: tuple, central: bool = False
):
    """Returns second-order finite difference & compares to force difference."""

    d2E = (three_scalars[2] - 2 * three_scalars[1] + three_scalars[0]) / STEP ** 2

    if central:
        dF = (two_derivatives[1] - two_derivatives[0]) / (4 * STEP)
    else:
        dF = (two_derivatives[1] - two_derivatives[0]) / (2 * STEP)

    SECOND_DERIVATIVES.append(dF)

    return d2E, abs(d2E - dF)


def _calculate_central_difference(i, order):
    """Returns first or second order central difference derivative."""

    if order == "second":

        return _calculate_second_order_difference(
            three_scalars=(SCALARS[i - 1], SCALARS[i], SCALARS[i + 1]),
            two_derivatives=(
                DERIVATIVES[i - 1],
                DERIVATIVES[i + 1],
            ),
            central=True,
        )

    return _calculate_first_order_difference(
        two_scalars=(SCALARS[i - 1], SCALARS[i + 1]), one_derivative=DERIVATIVES[i]
    )


def _calculate_forward_difference(i, order):
    """Returns first or second order forward difference derivative."""

    if order == "second":

        return _calculate_second_order_difference(
            three_scalars=(SCALARS[i], SCALARS[i + 1], SCALARS[i + 2]),
            two_derivatives=(DERIVATIVES[i], DERIVATIVES[i + 1]),
        )

    return _calculate_first_order_difference(
        two_scalars=(SCALARS[i], SCALARS[i + 1]), one_derivative=DERIVATIVES[i]
    )


def _calculate_backward_difference(i, order):
    """Returns first or second order backward difference derivative."""

    if order == "second":

        return _calculate_second_order_difference(
            three_scalars=(SCALARS[i - 2], SCALARS[i - 1], SCALARS[i]),
            two_derivatives=(DERIVATIVES[i - 1], DERIVATIVES[i]),
        )

    return _calculate_first_order_difference(
        two_scalars=(SCALARS[i - 1], SCALARS[i]), one_derivative=DERIVATIVES[i]
    )


def _format_results(diff_type, diff_order):
    """Returns modified-length DFT energy and force lists."""

    if diff_order == "second":
        return SCALARS, SECOND_DERIVATIVES

    if diff_type == "central":
        return [SCALARS[i] for i in range(1, N, 2)], [
            DERIVATIVES[i] for i in range(2, N - 1, 2)
        ]
    elif diff_type == "forward":
        return SCALARS, DERIVATIVES[:-1]
    else:
        return SCALARS, DERIVATIVES[1:]


def _display_results(
    params, exact_derivatives, finite_differences, deltas, environ=True
):
    """Displays finite differences against forces and compares them."""

    print()
    print(
        "{}-order {} finite difference".format(
            params["diff_order"], params["diff_type"]
        )
    )
    print("atom number  = {}".format(params["atom_to_perturb"]))
    print("n-steps      = {}".format(params["n_steps"]))
    print("d{}           = {:.2f}".format("x", params["step_sizes"][0]))
    print("d{}           = {:.2f}".format("y", params["step_sizes"][1]))
    print("d{}           = {:.2f}".format("z", params["step_sizes"][2]))
    print("Environ      = {}".format(environ))
    # print('doublecell  = {}'.format(double_cell))
    print()

    # display = {
    #     "Environ": exact_derivatives,
    #     "Finite": finite_differences,
    #     "\u0394F": deltas
    # }


@calcfunction
def calculate_finite_differences(
    pk_list: List, test_settings: Dict, environ: Bool = lambda: Bool(True)
) -> Dict:
    """
    Returns finite differences for a PK list and test settings.

    Inputs:
        pk_list:        aiida.orm.List
        test_settings:  aiida.orm.Dict
        environ:        aiida.orm.Bool

    Outputs:
        data:           aiida.orm.Dict
    """

    settings = test_settings.get_dict()
    diff_type = settings["diff_type"]
    diff_order = settings["diff_order"]

    dr = sum([component ** 2 for component in settings["step_sizes"]]) ** 0.5
    initial = _setup(pk_list.get_list(), dr, environ.value)

    finite_differences = []
    deltas = []

    # *** CALCULATE FINITE DIFFERENCES ***

    for i in range(N):

        if diff_type == "central" and 0 < i < (N - 1):

            if diff_order == "first" and i % 2 == 0:
                df, delta = _calculate_central_difference(i, diff_order)
            elif diff_order == "second":
                df, delta = _calculate_central_difference(i, diff_order)
            else:
                continue

            finite_differences.append(df)
            deltas.append(delta)

        elif diff_type == "forward" and i < (N - 1):

            if diff_order == "second" and i == (N - 2):
                continue
            else:
                df, delta = _calculate_forward_difference(i, diff_order)
                finite_differences.append(df)
                deltas.append(delta)

        elif diff_type == "backward" and i > 0:

            if diff_order == "second" and i == 1:
                continue
            else:
                df, delta = _calculate_backward_difference(i, diff_order)
                finite_differences.append(df)
                deltas.append(delta)

    # *** FORMAT & RETURN RESULTS ***

    output_scalars, output_derivatives = _format_results(diff_type, diff_order)

    # FIXME aiida will not display print() lines during WorkChains
    # TODO write DataFrame and/or plot as SinglefileData and return with key in data dict?
    # TODO generalize display function
    _display_results(
        settings, output_derivatives, finite_differences, deltas, environ.value
    )

    data = Dict(
        dict={
            "Initial": initial,
            "Scalars": output_scalars,
            "Exact derivatives": output_derivatives,
            "Finite differences": finite_differences,
            "Deltas": deltas,
        }
    )

    return data
