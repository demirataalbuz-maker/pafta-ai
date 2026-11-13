import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from audit_laptop import classify
class Classification(unittest.TestCase):
 def test_unavailable_starter_not_pass(self):
  self.assertEqual(classify('starter',{'status':'error','error':{'type':'ADLaboratuvarı','where':'kod','msg':'missing'}}),'BLOCKED')
 def test_missing_real_cim_model_never_passes_a_starter(self):
  r={'status':'error','error':{'type':'SplunkHatası','where':'kod','msg':"Error in 'DataModelEvaluator': Data model 'Web' was not found."}}
  for kind in ('solution','starter','tahmin'):self.assertEqual(classify(kind,r),'BLOCKED')
 def test_missing_official_cim_macro_is_blocked(self):
  r={'status':'error','error':{'type':'SplunkHatası','where':'kod','msg':"The search specifies a macro 'drop_dm_object_name' that cannot be found."}}
  for kind in ('solution','starter'):self.assertEqual(classify(kind,r),'BLOCKED')
 def test_arbitrary_bad_model_name_is_not_an_installation_gate(self):
  r={'status':'error','error':{'type':'SplunkHatası','where':'kod','msg':"Data model 'TypoModel' was not found."}}
  self.assertEqual(classify('solution',r),'FAIL')
 def test_broken_reference_not_pass(self):
  self.assertEqual(classify('solution',{'status':'error','error':{'type':'NameError','where':'kod'}}),'FAIL')
 def test_starter_rejected_expected(self):
  self.assertEqual(classify('starter',{'status':'fail','checks':[{'ok':False}]}),'PASS')
  self.assertEqual(classify('starter',{'status':'error','error':{'type':'SyntaxError','where':'kod'}}),'PASS')
 def test_test_exception_is_not_expected_rejection(self):
  self.assertEqual(classify('starter',{'status':'fail','error':{'type':'NameError','where':'test'}}),'ERROR')
 def test_wrong_answer_then_test_error_still_rejects_starter(self):
  self.assertEqual(classify('starter',{'status':'fail','checks':[{'ok':False}],'error':{'type':'KeyError','where':'test'}}),'PASS')
 def test_internal_and_timeouts_not_pass(self):
  for s in ('internal','timeout','cancelled'):self.assertEqual(classify('starter',{'status':s}),'ERROR')
 def test_successful_starter_is_failure(self):self.assertEqual(classify('starter',{'status':'pass'}),'FAIL')
if __name__=='__main__':unittest.main()
