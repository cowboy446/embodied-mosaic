import json,tempfile,unittest
from pathlib import Path
from stock_campaign import classify
class CampaignTests(unittest.TestCase):
 def test_missing_report_does_not_retry(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(classify(d,1)['decision'],'stop_error')
 def test_retry_only_validated_layout_rejection(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'report.json').write_text(json.dumps({'status':'failed','phase':'stock_initialization'}));(p/'stock-initialization.json').write_text(json.dumps({'passed':False,'objects':[{'path':'bad','passed':False}]}))
   self.assertEqual(classify(d,0)['decision'],'retry_layout')
   (p/'report.json').write_text(json.dumps({'status':'failed','phase':'rollout'}));(p/'stock-initialization.json').write_text(json.dumps({'passed':True,'objects':[]}))
   r=classify(d,0);self.assertEqual(r['decision'],'stop_layout_pass');self.assertEqual(r['navigation_status'],'failed');self.assertFalse(r['settling_certified'])
 def test_bounded_placement_rejection_is_retryable(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'report.json').write_text(json.dumps({'status':'failed','phase':'asset_preparation'}))
   rejection={'failed_object':'item02','max_trials_per_object':2,'attempts':[{'path':'item02','conflicts':['wall']}]*2}
   (p/'stock-randomization-rejected.json').write_text(json.dumps(rejection))
   self.assertEqual(classify(d,0)['decision'],'retry_layout')
   rejection['attempts'].pop();(p/'stock-randomization-rejected.json').write_text(json.dumps(rejection))
   self.assertEqual(classify(d,0)['decision'],'stop_error')
 def test_geometry_pass_does_not_hide_tipping(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'report.json').write_text(json.dumps({'status':'stepped','phase':'rollout'}));(p/'stock-initialization.json').write_text(json.dumps({'passed':True,'objects':[]}))
   (p/'stock-dynamics.json').write_text(json.dumps({'summary':{'passed':False}}))
   self.assertEqual(classify(d,0)['decision'],'stop_stability_failure')
if __name__=='__main__':unittest.main()
