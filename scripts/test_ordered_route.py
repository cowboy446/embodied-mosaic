import unittest
from ordered_route import OrderedRoute, audit_ordered_samples
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
    def test_offline_audit_ignores_online_claims(self):
        route=[(0,0),(2,0),(2,2),(0,0)]
        def rows(points):return [{'time_s':i/150,'position':[*p,1]} for i,p in enumerate(points)]
        self.assertFalse(audit_ordered_samples(route,rows([(0,0),(2,2),(2,0),(0,0)]))['completed'])
        result=audit_ordered_samples(route,rows(route))
        self.assertTrue(result['completed'])
        self.assertEqual([x['sample_index'] for x in result['visits']],[1,2,3])
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):OrderedRoute([(0,0),(float('nan'),0)])
        with self.assertRaises(ValueError):OrderedRoute([(0,0),(1,0)]).update((float('inf'),0))
if __name__=='__main__':unittest.main()
