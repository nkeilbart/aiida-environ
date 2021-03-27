import numpy as np
def point_project(vec1, vec2, vecp):
    cross = np.cross(vec1, vec2)
    dot = np.dot(cross, vecp)
    cross_norm = np.sqrt(sum(cross**2))
    return (dot / cross_norm) * (cross / cross_norm)

def reflect_point(vec1, vec2, vecp):
    cross = np.cross(vec1, vec2)
    t = -(np.dot(cross, vecp) / np.dot(cross, cross))
    reflected_point = vecp + 2 * t * cross
    return reflected_point