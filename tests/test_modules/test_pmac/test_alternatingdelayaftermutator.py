from unittest import TestCase

import numpy as np
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.modules.pmac.util import AlternatingDelayAfterMutator


class TestAlternatingDelayAfterMutator(TestCase):
    def setUp(self):
        self.line = LineGenerator("theta", "deg", 0.0, 180.0, 1801)
        self.base_generator = CompoundGenerator([self.line], duration=1.0)
        self.base_generator.prepare()
        self.alternating_mutator = AlternatingDelayAfterMutator(1.0, 5.0)

    def test_mutator_mutates_single_even_point(self):
        index = 2
        point = self.base_generator.get_point(index)
        assert point.delay_after == 0

        altered_point = self.alternating_mutator.mutate(point, index)

        assert altered_point.delay_after == 1.0

    def test_mutator_mutates_single_odd_point(self):
        index = 21
        point = self.base_generator.get_point(index)
        assert point.delay_after == 0

        altered_point = self.alternating_mutator.mutate(point, index)

        assert altered_point.delay_after == 5.0

    def test_mutator_mutates_even_number_of_multiple_points(self):
        indices = [10, 11, 12, 13, 14, 15]
        points = self.base_generator.get_points(indices[0], indices[-1] + 1)
        assert len(points) == 6

        altered_points = self.alternating_mutator.mutate(points, indices)

        for point in altered_points:
            if point.indexes % 2 == 0:
                assert point.delay_after == 1.0
            else:
                assert point.delay_after == 5.0

    def test_mutator_mutates_odd_number_of_multiple_points(self):
        indices = [11, 12, 13]
        points = self.base_generator.get_points(indices[0], indices[-1] + 1)
        assert len(points) == 3

        altered_points = self.alternating_mutator.mutate(points, indices)

        for point in altered_points:
            if point.indexes % 2 == 0:
                assert point.delay_after == 1.0
            else:
                assert point.delay_after == 5.0

    def test_mutator_mutates_multiple_points_with_non_continuous_indices(self):
        indices = [7, 200, 1, 99, 150, 3]
        points = self.base_generator.get_points(0, 6)

        altered_points = self.alternating_mutator.mutate(points, indices)

        for point, index in zip(altered_points, indices):
            if index % 2 == 0:
                assert point.delay_after == 1.0
            else:
                assert point.delay_after == 5.0

    def test_mutator_rasies_AssertionError_for_single_point_multiple_indices(self):
        indices = [1, 2]
        point = self.base_generator.get_point(0)

        self.assertRaises(
            AssertionError, self.alternating_mutator.mutate, point, indices
        )

    def test_mutator_rasies_AssertionError_for_multiple_points_with_single_index(self):
        index = 3
        points = self.base_generator.get_points(1, 5)

        self.assertRaises(
            AssertionError, self.alternating_mutator.mutate, points, index
        )

    def test_mutator_accepts_NumPy_indices(self):
        # Single point
        index = np.int64(5)
        point = self.base_generator.get_point(0)

        self.alternating_mutator.mutate(point, index)

        # Multiple points
        indices = np.array([2, 4, 6, 8], dtype=np.int64)
        points = self.base_generator.get_points(0, 3)

        self.alternating_mutator.mutate(points, indices)
