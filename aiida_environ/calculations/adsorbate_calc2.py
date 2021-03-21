import numpy as np
def vec_check_equivalence(vec1, vec2, vec3):
    cross = np.cross(vec1, vec2)
    dot = np.dot(cross, vec3)
    cross_norm = np.sqrt(sum(cross_norm**2))
    return (cross / cross_norm) * (dot / cross_norm)