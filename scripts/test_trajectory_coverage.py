import unittest
from trajectory_coverage import measure

def rows(points):
    return [{'time_s': i / 30, 'position': [*p, 1]} for i, p in enumerate(points)]

class CoverageTests(unittest.TestCase):
    def test_loop_does_not_increase_unique_coverage(self):
        line = [(i / 10, 0) for i in range(101)]
        once = measure(rows(line))
        loop = measure(rows(line + line[-2::-1]))
        self.assertAlmostEqual(once['executed_xy_length_m'], 10)
        self.assertAlmostEqual(loop['executed_xy_length_m'], 20)
        self.assertEqual(loop['visited_grid_cells'], once['visited_grid_cells'])
        self.assertEqual(loop['start_to_finish_m'], 0)
        self.assertEqual(loop['maximum_distance_from_start_m'], 10)
    def test_invalid_records(self):
        for data in ([], rows([(float('nan'), 0)]), rows([(0, 0)]) * 2):
            with self.assertRaises(ValueError): measure(data)
    def test_stationary(self):
        r = measure(rows([(0, 0)] * 30))
        self.assertEqual(r['executed_xy_length_m'], 0)
        self.assertEqual(r['visited_grid_cells'], 1)

if __name__ == '__main__': unittest.main()
