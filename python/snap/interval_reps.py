"""
Creating a group representation from shape *intervals*,
specifically elements of Sage's ComplexIntervalField.  Also contains
some utility functions for dealing with such representations.
"""

from .polished_reps import ManifoldGroup
from .fundamental_polyhedron import *

def diameter(A):
    return max(x.diameter() for x in A.list())

def holonomy_from_shape_intervals(manifold, shape_intervals,
                                  fundamental_group_args = [], lift_to_SL2 = True):
    """
    Returns the representation

        rho: pi_1(manifold) -> (P)SL(2, ComplexIntervalField)

    determined by the given shape_intervals.  If shape_intervals
    contains an exact solution z0 to the gluing equations with
    corresponding holonomy representation rho0, then for all g the
    ComplexIntervalField matrix rho(g) contains rho0(g)::

        sage: M = Manifold('m004(1,2)')
        sage: success, shapes = M.verify_hyperbolicity(bits_prec=53)
        sage: success
        True
        sage: rho = holonomy_from_shape_intervals(M, shapes)
        sage: (rho('a').det() - 1).contains_zero()
        True

    Of course, for long words the matrix entries will smear out::

        sage: diameter(rho('a')).log10() # doctest: +NUMERIC0
        -10.9576580520835
        sage: diameter(rho(10*'abAB')).log10() # doctest: +NUMERIC0
        -8.39987365046327
    """

    M = manifold
    G = M.fundamental_group(*fundamental_group_args)
    f = FundamentalPolyhedronEngine.from_manifold_and_shapes(
        M, shape_intervals, normalize_matrices = True)
    mats = f.matrices_for_presentation(G, match_kernel = True)
    PG = ManifoldGroup(G.generators(), G.relators(),
                       G.peripheral_curves(), mats)
    if lift_to_SL2:
        PG.lift_to_SL2C()
    return PG
