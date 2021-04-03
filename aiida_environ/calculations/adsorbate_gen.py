import numpy as np
from itertools import combinations
def generate(size, n):
    flat = size[0] * size[1]
    perms = []
    for positions in combinations(range(flat), n):
        p = [0] * flat
        for i in positions:
            p[i] = 1
        p = np.array(p).reshape(size)
        perms.append(p)
    return perms

def test_reflective(perm1, perm2):
    refs = [np.flip(perm1, 0), np.flip(perm1, 1)]
    for i in refs:
        if (i == perm2).all():
            return True
    return False

# def test_translation(perm1,perm2): <- Difficult

def test_rotation(perm1,perm2):
    refs = [np.rot90(np.rot90(perm1))]
    if np.array(perm1).shape[0] == np.array(perm1).shape[1]:
        refs.extend([np.rot90(perm1), np.rot90(np.rot90(np.rot90(perm1)))])
    for i in refs:
        if (i == perm2).all():
            return True
    return False

def final(size):
    n = size[0] * size[1]
    perms = []
    case0 = np.zeros(size)
    perms.append(case0)
    case0[0][0] = 1
    perms.append(case0)
    if (n > 1):
        case_n = np.ones(size)
        perms.append(case_n)
    for i in range(2, n):
        inner_perms = generate(size, i)
        print(inner_perms)
        j = 0
        while (j < len(inner_perms) - 1):
            perm1 = inner_perms[j]
            temp = inner_perms[j + 1:]
            count = 0
            for k, perm2 in temp:
                if test_reflective(perm1, perm2) or test_translation(perm1, perm2) or test_rotation(perm1,perm2):
                    inner_perms.pop(k + j + 1 - count)
                    count += 1
            j += 1
        perms.extend(inner_perms)
    return perms