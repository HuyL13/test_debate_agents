import copy
import unittest
import test_warrants_v2
from warrant_slots_v2 import canonicalize_slots,slot_schema
class WarrantSlotTests(unittest.TestCase):
    setUp=test_warrants_v2.RoleGroundedTypingTests.setUp
    def test_concession_warrant_is_code_owned_without_an_api_call(self):
        from warrant_slots_v2 import type_warrant_slots
        annotation=copy.deepcopy(self.annotation);annotation['applications'][0]['kind']='concession'
        def forbidden(*args,**kwargs):raise AssertionError('No model needed for non-argumentative warrant')
        result=type_warrant_slots({'sample_id':'fixed'},self.units,annotation,invoke_fn=forbidden)
        self.assertEqual(result['status'],'not_applicable')
        self.assertEqual(result['output']['annotations']['a0']['scheme'],'other')
    def test_nonargumentative_ids_are_not_requested_from_model(self):
        from warrant_slots_v2 import type_warrant_slots
        annotation=copy.deepcopy(self.annotation)
        concession=copy.deepcopy(annotation['applications'][0]);concession['kind']='concession';annotation['applications'].append(concession)
        def fake(model,stage,sid,prompt,payload,validator,version,repeat,settings):
            self.assertEqual([a['id'] for a in payload['applications']],['a0'])
            out=self.raw();validator(out)
            return {'status':'accepted','call_id':'fake','output':out}
        result=type_warrant_slots({'sample_id':'mixed'},self.units,annotation,invoke_fn=fake)
        self.assertEqual(result['output']['annotations']['a1']['scheme'],'other')
    def raw(self):
        t=self.output['annotations']['a0'];return {'annotations':{'a0':{'warrant':dict(scheme=t['scheme'],scope_change=t['scope_change'],alternatives=t['alternatives'],roles={'tradition':[0],'claim':[1]}), 'evidence':t['evidence'],'reason':t['reason']}}}
    def test_slots_compile_to_the_same_grounded_roles(self):
        self.assertEqual(canonicalize_slots(self.raw(),self.annotation,self.units),self.output)
    def test_missing_required_named_role_is_rejected(self):
        raw=self.raw();raw['annotations']['a0']['warrant']['roles'].pop('tradition')
        with self.assertRaises(ValueError):canonicalize_slots(raw,self.annotation,self.units)
    def test_source_schema_excludes_testimony_when_no_reported_premise_exists(self):
        schema=slot_schema(self.annotation,self.units)
        branches=schema['properties']['annotations']['properties']['a0']['properties']['warrant']['anyOf']
        self.assertNotIn('testimony',[b['properties']['scheme']['enum'][0] for b in branches])
    def test_claim_schema_only_allows_actual_target(self):
        schema=slot_schema(self.annotation,self.units)
        branches=schema['properties']['annotations']['properties']['a0']['properties']['warrant']['anyOf']
        history=next(b for b in branches if b['properties']['scheme']['enum']==['historical_practice'])
        self.assertEqual(history['properties']['roles']['properties']['claim']['items']['enum'],[1])
