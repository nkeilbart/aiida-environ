# -*- coding: utf-8 -*-
from copy import deepcopy
from typing import List


class Occupancy:
    def __init__(self, pps: List, aps: List):
        assert len(pps) == len(aps)
        n = len(pps)
        self.pps = pps
        self.aps = aps
        self.configuration = []
        for i in range(n):
            inner_configuration = [0] * pps[i]
            self.configuration.append(inner_configuration)
        # hack to enforce initial iterable
        self.configuration[-1][-1] = -1

    def __str__(self):
        return self.configuration.__str__()

    def __repr__(self):
        return self.configuration.__repr__()

    def __iter__(self):
        return self

    def clone(self):
        clone = Occupancy(self.pps, self.aps)
        clone.configuration = deepcopy(self.configuration)
        return clone

    def next_inner(self, inner, index):
        result = deepcopy(inner)
        i = len(result) - 1
        while True:
            result[i] += 1
            if result[i] <= self.aps[index]:
                if i < len(result) - 1:
                    j = i + 1
                    while j < len(result):
                        result[j] = result[i]
                        j += 1
                return result
            else:
                result[i] = 0
                i -= 1
                if i < 0:
                    return None

    def __next__(self):
        i = len(self.configuration)
        while True:
            i -= 1
            if i < 0:
                raise StopIteration
            temp = self.next_inner(self.configuration[i], i)
            if temp is not None:
                self.configuration[i] = temp
                return self.clone()
            else:
                self.configuration[i] = [0] * self.pps[i]

    def __sub__(self, other):
        assert self.pps == other.pps
        assert self.aps == other.aps
        diff = 0
        n = len(self.pps)
        for i in range(n):
            temp = deepcopy(other.configuration)
            for j, val in enumerate(self.configuration[i]):
                if val in temp[i]:
                    temp[i][temp[i].index(val)] = -1
                else:
                    diff += 1
        return diff
