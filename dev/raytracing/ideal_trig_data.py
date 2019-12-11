from snappy.snap import t3mlite as t3m
from snappy import Triangulation

from snappy.SnapPy import matrix

from snappy.snap.mcomplex_base import *

from snappy.verify.cuspCrossSection import *

from hyperboloid_utilities import *

def _matrix_taking_0_1_inf_to_given_points(z0, z1, zinf):
    l = z1   - z0
    m = zinf - z1
        
    return matrix([[ l * zinf, m * z0 ],
                   [ l,        m      ]])

def _pgl2_matrix_for_face(tet, F):
    gluing = tet.Gluing[F]
    other_tet = tet.Neighbor[F]
    verts = [
        tet.complex_vertices[V]
        for V in t3m.ZeroSubsimplices
        if V & F ]
    other_verts = [
        other_tet.complex_vertices[gluing.image(V)]
        for V in t3m.ZeroSubsimplices
        if V & F ]
        
    m1 = _matrix_taking_0_1_inf_to_given_points(*verts)
    m2 = _matrix_taking_0_1_inf_to_given_points(*other_verts)
    
    return m2 * _adjoint(m1)

def _o13_matrix_for_face(tet, F):
    return GL2C_to_O13(_pgl2_matrix_for_face(tet, F))

def _invDiff(a, b):
    if a == Infinity:
        return 0
    return 1 / (a - b)

def _compute_cusp_triangle_vertex_positions(tet, V, i):

    z  = tet.ShapeParameters[t3m.E01]
    CF = z.parent()

    triangle = tet.horotriangles[V]
    otherVerts = [ t3m.ZeroSubsimplices[(i + j) % 4] for j in range(1, 4) ]
    vertex_positions = [ triangle.vertex_positions[V | otherVert ]
                         for otherVert in otherVerts ]

    fixed_point = triangle.fixed_point
    if fixed_point is None:
        m_translation, l_translation = tet.Class[V].Translations

        a, c = m_translation.real(), m_translation.imag()
        b, d = l_translation.real(), l_translation.imag()

        log_z0 = CF(0)

        # Inverting matrix here since SageMath screws up :(
        translations_to_ml = matrix([[d,-b], [-c, a]]) / (a*d - b * c)
    
        vertex_positions = [ translations_to_ml * complex_to_pair(z)
                             for z in vertex_positions ]

    else:
        log_z0 = triangle.lifted_vertex_positions[V | otherVerts[0]]
        vertex_positions = [ z - fixed_point for z in vertex_positions ]
        z0 = vertex_positions[0]
        vertex_positions = [ complex_to_pair(z / z0)
                             for z in vertex_positions ]

    return log_z0, vertex_positions

def _compute_triangle_heights(tet):
    z  = tet.ShapeParameters[t3m.E01]
    CF = z.parent()

    z0 = CF(0)
    z1 = CF(1)
    z2 = z
    return [ height_euclidean_triangle(z0, z1, z2),
             height_euclidean_triangle(z1, z2, z0),
             height_euclidean_triangle(z2, z0, z1) ]

def _compute_ideal_and_finite_point_on_horosphere_for_vertex(tet, V0):
    V1, V2, V3 = t3m.VerticesOfFaceCounterclockwise[t3m.comp(V0)]

    cusp_length = tet.horotriangles[V0].get_real_lengths()[V0 | V1 | V2]
    pts  = [ tet.complex_vertices[V] for V in [V0, V1, V2]]
    if pts[0] != Infinity:

        pts[1] = _invDiff(pts[1], pts[0])
        pts[2] = _invDiff(pts[2], pts[0])

    base_length = abs(pts[2] - pts[1])
    
    if pts[0] != Infinity:
        return pts[0], (pts[0], cusp_length / base_length)
    else:
        return pts[0], (pts[1], base_length / cusp_length)

def _compute_R13_horosphere_for_vertex(tet, V0):
    ideal_point, (z, t) = _compute_ideal_and_finite_point_on_horosphere_for_vertex(
        tet, V0)

    light_vector = complex_to_R13_light_vector(ideal_point)
    
    horosphere_point = complex_and_height_to_R13_time_vector(z, t)

    s = -R13_dot(light_vector, horosphere_point)

    return [ x / s for x in light_vector ]

def _compute_so13_edge_involutions_for_tet(tet):
    return {
        edge : compute_so13_edge_involution(
            tet.complex_vertices[t3m.simplex.Tail[edge]],
            tet.complex_vertices[t3m.simplex.Head[edge]])
        for edge in t3m.simplex.OneSubsimplices }

def _adjoint(m):
    return matrix([[ m[1,1], -m[0,1]],
                   [-m[1,0],  m[0,0]]], ring = m[0,0].parent())

def _compute_gl2c_edge_involution_for_tet_and_vertex(tet, vertex):
    trig = tet.horotriangles[vertex]
    
    fixed_point = trig.fixed_point
    if fixed_point is None:
        CF = tet.ShapeParameters[t3m.E01].parent()
        return matrix([[0,0], [0,0]], ring = CF)
    
    tet_vertices  = [ tet.complex_vertices[v]
                     for v in t3m.ZeroSubsimplices
                     if v != vertex ]

    cusp_vertices = [ trig.vertex_positions[vertex | v]
                      for v in t3m.ZeroSubsimplices
                      if v != vertex ]
    
    std_to_tet = _matrix_taking_0_1_inf_to_given_points(*tet_vertices)
    cusp_to_std = _adjoint(_matrix_taking_0_1_inf_to_given_points(*cusp_vertices))

    cusp_to_tet = std_to_tet * cusp_to_std

    involution = matrix([[-1, 2 * trig.fixed_point],
                         [ 0, 1]])
    
    return cusp_to_tet * involution * _adjoint(cusp_to_tet)

def _compute_so13_edge_involution_for_tet_and_vertex(tet, vertex):
    m = _compute_gl2c_edge_involution_for_tet_and_vertex(tet, vertex)

    if m == matrix([[0,0], [0,0]]):
        return matrix([[0, 0, 0, 0],
                       [0, 0, 0, 0],
                       [0, 0, 0, 0],
                       [0, 0, 0, 0]])

    return GL2C_to_O13(m)

class IdealTrigRaytracingData(McomplexEngine):
    @staticmethod
    def from_manifold(manifold, areas = 0.1, insphere_scale = 0.05):

        snappy_trig = Triangulation(manifold)
        snappy_trig.dehn_fill(snappy_trig.num_cusps() * [(0,0)])

        c = ComplexCuspCrossSection.fromManifoldAndShapes(
            manifold,
            manifold.tetrahedra_shapes('rect'),
            one_cocycle = 'develop')
        c.normalize_cusps(areas)
        c.compute_translations()
        c.add_vertex_positions_to_horotriangles()
        c.add_fixed_point_to_horotriangles()
        c.lift_vertex_positions_of_horotriangles()

        r = IdealTrigRaytracingData(c.mcomplex, manifold)
        r.insphere_scale = insphere_scale
        r.areas = areas
        r.peripheral_gluing_equations = snappy_trig.gluing_equations()[
            snappy_trig.num_tetrahedra():]

        # For debugging! Delete!
        r.c = c

        r._add_triangle_heights()
        r._add_complex_vertices()
        r._add_R13_vertices()
        r._add_O13_matrices_to_faces()
        r._add_R13_planes_to_faces()
        r._add_R13_horospheres_to_vertices()
        r._add_so13_edge_involutions()
        r._add_so13_cusp_edge_involutions()
        r._add_inspheres()
        r._add_log_holonomies()

        r._add_cusp_triangle_vertex_positions()
        return r

    def __init__(self, mcomplex, snappy_manifold):
        super(IdealTrigRaytracingData, self).__init__(mcomplex)
        self.snappy_manifold = snappy_manifold

    def _add_triangle_heights(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.triangle_heights = _compute_triangle_heights(tet)

    def _add_O13_matrices_to_faces(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.O13_matrices = {
                F: _o13_matrix_for_face(tet, F)
                for F in t3m.TwoSubsimplices }

    def _add_complex_vertices(self):
        for tet in self.mcomplex.Tetrahedra:
            z = tet.ShapeParameters[t3m.E01]
            w = z.sqrt() + (z-1).sqrt()
            tet.complex_vertices = {
                t3m.V0 :       w,
                t3m.V1 :   1 / w,
                t3m.V2 : - 1 / w,
                t3m.V3 : -     w }

    def _add_R13_vertices(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.R13_vertices = {
                V: complex_to_R13_light_vector(z)
                for V, z in tet.complex_vertices.items() }

    def _add_R13_planes_to_faces(self):
        for tet in self.mcomplex.Tetrahedra:
            planes = make_tet_planes(
                [ tet.R13_vertices[v]
                  for v in t3m.ZeroSubsimplices])
            tet.R13_planes = {
                F : plane
                for F, plane in zip(t3m.TwoSubsimplices, planes) }

    def _add_R13_horospheres_to_vertices(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.R13_horospheres = {
                V : _compute_R13_horosphere_for_vertex(tet, V)
                for V in t3m.ZeroSubsimplices }

    def _add_cusp_triangle_vertex_positions(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.cusp_triangle_vertex_positions = {
                V : _compute_cusp_triangle_vertex_positions(tet, V, i)
                for i, V in enumerate(t3m.ZeroSubsimplices) }

    def _add_so13_edge_involutions(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.so13_edge_involutions = _compute_so13_edge_involutions_for_tet(
                tet)

    def _add_so13_cusp_edge_involutions(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.so13_cusp_edge_involutions = {
                vertex : _compute_so13_edge_involution_for_tet_and_vertex(tet, vertex)
                for vertex in t3m.ZeroSubsimplices }

    def _add_inspheres(self):
        for tet in self.mcomplex.Tetrahedra:
            tet.inradius = tet.R13_planes[t3m.F0][0].arcsinh()

            tmp = tet.inradius * self.insphere_scale

            tet.cosh_sqr_inradius = tmp.cosh() ** 2

    def _add_log_holonomies_to_cusp(self, cusp, shapes):
        i = cusp.Index

        m_log, l_log = [
            sum(shape * expo
                for shape, expo
                in zip(shapes, self.peripheral_gluing_equations[2 * i + j]))
            for j in range(2) ]

        a, c = m_log.real(), m_log.imag()
        b, d = l_log.real(), l_log.imag()
            
        det = a*d - b * c
        cusp.mat_log = matrix([[d,-b], [-c, a]]) / det
                
        slope = 2 * self.areas[i] / abs(det)

        x = (slope ** 2 / (slope ** 2 + 1)).sqrt()
        y = (1 / (slope ** 2 + 1)).sqrt()
        cusp.coshCuspEdgeThickness = 1 + (x ** 2 + (1 - y) ** 2) / (2 * y)

    def _add_log_holonomies(self):
        shapes = [
            tet.ShapeParameters[e].log()
            for tet in self.mcomplex.Tetrahedra
            for e in [ t3m.E01, t3m.E02, t3m.E03 ] ]

        for cusp, cusp_info in zip(self.mcomplex.Vertices,
                                   self.snappy_manifold.cusp_info()):
            if cusp_info['complete?']:
                cusp.mat_log = matrix([[1,0],[0,1]])
                cusp.coshCuspEdgeThickness = 0.0
            else:
                self._add_log_holonomies_to_cusp(cusp, shapes)

    def get_initial_tet_num(self):
        return 0

    def get_uniform_bindings(self):
        otherTetNums = [
            tet.Neighbor[F].Index
            for tet in self.mcomplex.Tetrahedra
            for F in t3m.TwoSubsimplices ]

        enteringFaceNums = [
            tet.Gluing[F][f]
            for tet in self.mcomplex.Tetrahedra
            for f, F in enumerate(t3m.TwoSubsimplices) ]

        triangle_heights = [
            height
            for tet in self.mcomplex.Tetrahedra
            for height in tet.triangle_heights ]

        triangle_height_vectors = [
            tet.triangle_heights
            for tet in self.mcomplex.Tetrahedra ]

        SO13tsfms = [
            tet.O13_matrices[F]
            for tet in self.mcomplex.Tetrahedra
            for F in t3m.TwoSubsimplices ]

        planes = [
            tet.R13_planes[F]
            for tet in self.mcomplex.Tetrahedra
            for F in t3m.TwoSubsimplices ]

        horospheres = [
            tet.R13_horospheres[V]
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices ]

        SO13EdgeInvolutions = [
            tet.so13_edge_involutions[E]
            for tet in self.mcomplex.Tetrahedra
            for E in t3m.OneSubsimplices[:3] ]

        SO13CuspEdgeInvolutions = [
            tet.so13_cusp_edge_involutions[V]
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices ]            

        coshCuspEdgeThickness = [
            tet.Class[V].coshCuspEdgeThickness
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices ]            

        logAdjustments = [
            complex_to_pair(tet.cusp_triangle_vertex_positions[V][0])
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices ]

        plane_dist_to_complex_coordinates = [
            tet.cusp_triangle_vertex_positions[V][1]
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices
            ]

        mat_logs = [
            tet.Class[V].mat_log
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices ]

        insphere_radii = [
            tet.cosh_sqr_inradius
            for tet in self.mcomplex.Tetrahedra ]

        edge_color_indices = [
            tet.Class[E].Index
            for tet in self.mcomplex.Tetrahedra
            for E in t3m.OneSubsimplices ]

        horosphere_color_indices = [
            tet.Class[V].Index
            for tet in self.mcomplex.Tetrahedra
            for V in t3m.ZeroSubsimplices ]

        return {
            'otherTetNums' :
                ('int[]', otherTetNums),
            'enteringFaceNums' :
                ('int[]', enteringFaceNums),
            'SO13tsfms' :
                ('mat4[]', SO13tsfms),
            'planes' :
                ('vec4[]', planes),
            'horospheres' :
                ('vec4[]', horospheres),
            'SO13EdgeInvolutions' :
                ('mat4[]', SO13EdgeInvolutions),
            'SO13CuspEdgeInvolutions' :
                ('mat4[]', SO13CuspEdgeInvolutions),
            'coshCuspEdgeThickness' :
                ('float[]', coshCuspEdgeThickness),
            'logAdjustments' :
                ('vec2[]', logAdjustments),
            'planeDistToComplexCoordinates' :
                ('mat3x2[]', plane_dist_to_complex_coordinates),
            'triangleHeights' :
                ('float[]', triangle_heights),
            'triangleHeightVectors' :
                ('vec3[]', triangle_height_vectors),
            'matLogs' :
                ('mat2[]', mat_logs),
            'insphere_radii' :
                ('float[]', insphere_radii),
            'edge_color_indices' :
                ('int[]', edge_color_indices),
            'horosphere_color_indices' :
                ('int[]', horosphere_color_indices) }

    def get_compile_time_constants(self):
        return {
            b'##num_tets##' : len(self.mcomplex.Tetrahedra)
            }

    def update_view_state(self, boost_and_tet_num, m):
        boost, tet_num = boost_and_tet_num

        boost = O13_orthonormalize(boost * m)

        entry_F = -1

        for i in range(100):
            pos = boost.transpose()[0]
            tet = self.mcomplex.Tetrahedra[tet_num]

            amount, F = max(
                [ (R13_dot(pos, tet.R13_planes[F]), F)
                  for F in t3m.TwoSubsimplices ])

            if F == entry_F:
                break
            if amount < 0.0000001:
                break
            
            boost = O13_orthonormalize(tet.O13_matrices[F] * boost)
            tet_num = tet.Neighbor[F].Index
            entry_F = tet.Gluing[F].image(F)

        return boost, tet_num
