# -*- coding: utf-8 -*-
from math import ceil


def get_charge_range(cmax, cinc):
    n = int(ceil(cmax / cinc) * 2 + 1)
    carr = [0.0] * n
    for i in range(n):
        j = i - (n // 2)
        carr[i] = cinc * j
    return carr
