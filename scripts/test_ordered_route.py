import unittest
from ordered_route import OrderedRoute
class OrderedTests(unittest.TestCase):
    def test_early_endpoint_is_not_success(self):
        route=OrderedRoute([(0,0),(2,0),(2,2),(0,0)])
        self.assertFalse(route.update((0,0)))
        self.assertFalse(route.update((2,2)))
        self.assertFalse(route.update((2,0)))
        self.assertFalse(route.update((0,0)))
        self.assertFalse(route.update((2,2)))
        self.assertTrue(route.update((0,0)))
        self.assertTrue(route.summary()['completed'])
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):OrderedRoute([(0,0),(float('nan'),0)])
        with self.assertRaises(ValueError):OrderedRoute([(0,0),(1,0)]).update((float('inf'),0))
if __name__=='__main__':unittest.main()
