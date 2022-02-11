# -*- coding: utf-8 -*-
from dataclasses import dataclass

from aiida_environ.utils.occupancy import Occupancy


@dataclass
class Vertex:
    occ: Occupancy
    connections: int = 0


class Graph:
    def __init__(self):
        self.vertices = []
        self.edges = {}

    def add_vertex(self, occ):
        self.vertices.append(Vertex(occ))

    def add_edge(self, v1, v2):
        if v1 not in self.edges:
            self.edges[v1] = {}
        elif v2 not in self.edges[v1]:
            self.edges[v1][v2] = 1
        self.vertices[v1].connections += 1

        if v2 not in self.edges:
            self.edges[v2] = {}
        elif v1 not in self.edges[v2]:
            self.edges[v2][v1] = 1
        self.vertices[v2].connections += 1

    def get_vertices_with_connections(self, n):
        occ_list = []
        for v in self.vertices:
            if v.connections == n:
                occ_list.append(v.occ)
        return occ_list
