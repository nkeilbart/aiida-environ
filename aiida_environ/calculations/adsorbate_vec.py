import numpy as np
def vec_point_dist(vec1, vec2, vecp):
    cross = np.cross(vec1, vec2)
    dot = np.dot(cross, vecp)
    cross_norm = np.sqrt(sum(cross**2))
    return dot / cross_norm