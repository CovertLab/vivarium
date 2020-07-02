'''
====================
Colony Shape Deriver
====================
'''

from __future__ import absolute_import, division, print_function

import alphashape
import numpy as np
from pytest import approx
from shapely.geometry.polygon import Polygon
from shapely.geometry.collection import GeometryCollection
from shapely.geometry.multipolygon import MultiPolygon

from vivarium.core.process import Deriver
from vivarium.processes.derive_colony_metric import assert_no_divide


def major_minor_axes(shape):
    '''Calculate the lengths of the major and minor axes of a shape

    We assume that the major and minor axes are the dimensions of the
    minimum bounding rectangle of the shape. Note that this is different
    from using PCA to find the axes, especially for highly asymmetrical
    and concave shapes.

    Arguments:
        shape (Polygon): The shape to compute axes for.

    Returns:
        Tuple[float, float]: A tuple with the major axis first and the
        minor axis second.
    '''
    rect = shape.minimum_rotated_rectangle
    points = list(rect.exterior.coords)
    points = [np.array(point) for point in points]
    # Shapely returns polygon coordinates in the order in which they
    # would appear while traversing the boundary, so we know that any 3
    # consecutive points span the major and minor axes
    dimension_1 = abs(np.linalg.norm(points[1] - points[0]))
    dimension_2 = abs(np.linalg.norm(points[2] - points[1]))
    major = max(dimension_1, dimension_2)
    minor = min(dimension_1, dimension_2)
    return major, minor


class ColonyShapeDeriver(Deriver):
    '''Derives colony shape metrics from cell locations
    '''

    defaults = {
        'agents_path': tuple(),
        'alpha': 1.0,
    }

    def ports_schema(self):
        return {
            'agents': {
                '*': {
                    'boundary': {
                        'location': {
                            '_default': [0.5, 0.5],
                        },
                    },
                },
            },
            'colony_global': {
                'surface_area': {
                    '_default': [],
                    '_updater': 'set',
                    '_divider': assert_no_divide,
                    '_emit': True,
                },
                'axes': {
                    '_default': [],
                    '_updater': 'set',
                    '_divider': assert_no_divide,
                    '_emit': True,
                },
            },
        }

    def next_update(self, timestep, states):
        agents = states['agents']
        points = [
            agent['boundary']['location']
            for agent in agents.values()
        ]
        alpha_shape = alphashape.alphashape(
            points, self.parameters['alpha'])
        if isinstance(alpha_shape, Polygon):
            shapes = [alpha_shape]
        else:
            assert isinstance(
                alpha_shape, (MultiPolygon, GeometryCollection))
            shapes = list(alpha_shape)

        # Calculate colony surface areas
        areas = [shape.area for shape in shapes]

        # Calculate colony major and minor axes based on bounding
        # rectangles
        axes = []
        for shape in shapes:
            if isinstance(shape, Polygon):
                axes.append(major_minor_axes(shape))
            else:
                axes.append((0, 0))

        # Calculate colony circumference
        circumference = [shape.length for shape in shapes]

        return {
            'colony_global': {
                'surface_area': areas,
                'axes': axes,
                'circumference': circumference,
            }
        }


class TestDeriveColonyShape():

    def calc_shape_metrics(self, points, agents_path=None, alpha=None):
        config = {}
        if agents_path is not None:
            config['agents_path'] = agents_path
        if alpha is not None:
            config['alpha'] = alpha
        deriver = ColonyShapeDeriver(config)
        states = {
            'agents': {
                str(i): {
                    'boundary': {
                        'location': list(point),
                    },
                }
                for i, point in enumerate(points)
            },
            'colony_global': {
                'surface_area': [],
                'axes': [],
            }
        }
        # Timestep does not matter
        update = deriver.next_update(-1, states)
        return update['colony_global']

    def flatten(self, lst):
        return [
            elem
            for sublist in lst
            for elem in sublist
        ]

    def test_convex(self):
        #    *
        #   / \
        #  * * *
        #   \ /
        #    *
        points = [
            (1, 2),
            (0, 1), (1, 1), (2, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        assert metrics['surface_area'] == [2]
        assert approx([np.sqrt(2), np.sqrt(2)]) == self.flatten(
            metrics['axes'])
        assert metrics['circumference'] == approx([4 * np.sqrt(2)])

    def test_concave(self):
        # *-*-*-*-*
        # |       |
        # * * *-*-*
        # |  /
        # * *
        # |  \
        # * * *-*-*
        # |       |
        # *-*-*-*-*
        points = (
            [(i, 4) for i in range(5)]
            + [(i, 3) for i in range(5)]
            + [(i, 2) for i in range(2)]
            + [(i, 1) for i in range(5)]
            + [(i, 0) for i in range(5)]
        )
        metrics = self.calc_shape_metrics(points)
        assert metrics['surface_area'] == [11]
        assert metrics['axes'] == [(4, 4)]
        assert metrics['circumference'] == approx([18 + 2 * np.sqrt(2)])

    def test_ignore_outliers(self):
        #    *
        #   / \
        #  * * *            *
        #   \ /
        #    *
        points = [
            (1, 2),
            (0, 1), (1, 1), (2, 1), (10, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        assert metrics['surface_area'] == [2]
        assert approx([np.sqrt(2), np.sqrt(2)]) == self.flatten(
            metrics['axes'])
        assert metrics['circumference'] == approx([4 * np.sqrt(2)])

    def test_colony_too_diffuse(self):
        #    *
        #
        #  *   *
        #
        #    *
        points = [
            (1, 2),
            (0, 1), (2, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        expected_metrics = {
            'surface_area': [],
            'axes': [],
            'circumference': [],
        }
        assert metrics == expected_metrics

    def test_find_multiple_colonies(self):
        #    *          *
        #   / \        / \
        #  * * *      * * *
        #   \ /        \ /
        #    *          *
        points = [
            (1, 2), (11, 2),
            (0, 1), (1, 1), (2, 1), (10, 1), (11, 1), (12, 1),
            (1, 0), (11, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        assert metrics['surface_area'] == [2, 2]
        assert self.flatten(metrics['axes']) == approx(
            [np.sqrt(2), np.sqrt(2), np.sqrt(2), np.sqrt(2)])
        assert metrics['circumference'] == approx([4 * np.sqrt(2)] * 2)
