import unittest
from evaluate_v2 import evaluate_rows, compare_repeats


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.units=[dict(id=0,source='comment',start=0,end=34,text='Most agree therefore adopt it now.')]
        self.p=[dict(unit=0,first=0,last=2,owner='current_author',speech_act='assert',implicit=False,event_role='none'),dict(unit=0,first=3,last=6,owner='current_author',speech_act='recommend',implicit=False,event_role='none')]
        self.row=dict(sample_id='x',status='ok',units=self.units,annotation=dict(propositions=self.p,applications=[dict(kind='support',premises=[0],target_kind='proposition',target=1,roles=[])]))
        self.ref=dict(id='r',sample_id='x',kind='support',expected='supported',premise_spans=[dict(source='comment',start=0,end=10)],target_span=dict(source='comment',start=21,end=34))

    def test_within_unit_direction_and_reverse(self):
        self.assertEqual(evaluate_rows([self.row],[self.ref])['positive_covered'],1)
        self.row['annotation']['applications'][0].update(premises=[1],target=0)
        out=evaluate_rows([self.row],[self.ref])
        self.assertEqual(out['positive_covered'],0)
        self.assertTrue(out['references'][0]['reversed'])

    def test_infrastructure_distinct_from_absence(self):
        self.row.update(status='error',annotation=None)
        out=evaluate_rows([self.row],[self.ref])
        self.assertEqual(out['infrastructure_failures'],1)
        self.assertEqual(out['references'][0]['status'],'infrastructure_failure')

    def test_projection_recommendation_control(self):
        self.row['annotation']['applications'][0]['kind']='projection'
        self.assertIn('projection_non_event',evaluate_rows([self.row],[])['controls'][0]['issues'])

    def test_recommended_initial_condition_is_valid(self):
        self.p[0].update(event_role='action',speech_act='recommend')
        self.p[1].update(event_role='outcome',speech_act='hypothetical')
        self.row['annotation']['applications'][0]['kind']='projection'
        self.assertEqual(evaluate_rows([self.row],[])['controls'][0]['issues'],[])
        self.p[1]['speech_act']='recommend'
        self.assertIn('projection_non_event',evaluate_rows([self.row],[])['controls'][0]['issues'])

    def test_implicit_assertion_is_hypothesis_by_contract(self):
        self.p[0]['implicit']=True
        self.assertEqual(evaluate_rows([self.row],[])['controls'][0]['issues'],[])

    def test_supplied_graph_can_reveal_implicit_promotion(self):
        self.p[0]['implicit']=True
        self.row['graph']={'nodes':[dict(type='Assertion',proposition='p0',status='explicit')],'edges':[]}
        self.assertIn('implicit_assertion_promoted',evaluate_rows([self.row],[])['controls'][0]['issues'])

    def test_near_miss_is_diagnostic_not_coverage(self):
        self.ref['premise_spans'][0]['end']=9
        out=evaluate_rows([self.row],[self.ref])
        self.assertEqual(out['positive_covered'],0)
        self.assertEqual(len(out['references'][0]['alignment_candidates']),1)
        self.assertEqual(out['references'][0]['alignment_candidates'][0]['status'],'manual_review_required')

    def test_alignment_never_ignores_direction(self):
        self.row['annotation']['applications'][0].update(premises=[1],target=0)
        self.assertEqual(evaluate_rows([self.row],[self.ref])['references'][0]['alignment_candidates'],[])

    def test_bad_annotation_is_quality_failure(self):
        self.row['annotation']['applications'][0]['target']=40
        out=evaluate_rows([self.row],[self.ref])
        self.assertEqual(out['quality_failures'],1)
        self.assertEqual(out['infrastructure_failures'],0)

    def test_quality_rejection_and_stage_infrastructure_are_separate(self):
        self.row.update(status='rejected',annotation=None,stage_status={'proposal':'infrastructure_error','witness':'rejected'},stage_call_ids={'witness':'call1'})
        out=evaluate_rows([self.row],[self.ref])
        self.assertEqual(out['infrastructure_failures'],0)
        self.assertEqual(out['quality_failures'],1)
        self.assertEqual(out['references'][0]['status'],'quality_failure')
        self.assertEqual(out['stage_quality_failure_counts'],{'witness':1})
        self.assertEqual(out['stage_infrastructure_failure_counts'],{'proposal':1})

    def test_repeat_uses_semantics_not_ids(self):
        self.assertEqual(compare_repeats([[self.row],[self.row]],[self.ref])['whole_stage_equal'],True)

    def test_ambiguous_negative_not_silently_relabeled(self):
        self.ref.update(expected='unsupported',ambiguity='plausible alternate reading')
        out=evaluate_rows([self.row],[self.ref])
        self.assertEqual(out['negative_accepted'],1)
        self.assertEqual(out['ambiguous_reference_count'],1)

    def test_role_changes_break_whole_stage_repeat(self):
        import copy
        changed=copy.deepcopy(self.row)
        changed['annotation']['applications'][0]['roles']=[dict(role='source',proposition=0)]
        self.assertFalse(compare_repeats([[self.row],[changed]],[self.ref])['whole_stage_equal'])

    def test_frozen_sources_and_primary_labels(self):
        import json
        from pathlib import Path
        root=Path(__file__).parent
        original=json.loads((root/'relation_retention_references.json').read_text(encoding='utf-8'))['references']
        refined=json.loads((root/'v2_audit_references.json').read_text(encoding='utf-8'))['references']
        byid={r['id']:r for r in refined}
        for r in original:
            self.assertEqual(byid[r['id']]['expected'],r['expected'])
            self.assertEqual(byid[r['id']]['kind'],r['kind'])
        fresh=json.loads((root/'v2_fresh_audit_manifest.json').read_text(encoding='utf-8'))
        ids={s['article_id'] for s in fresh['samples']}
        self.assertEqual(len(ids),16)
        self.assertFalse(ids & set(fresh['excluded_article_ids']))
        for s in fresh['samples']:self.assertEqual(s['split'],'induction')
        lookup={s['sample_id']:s for s in fresh['samples']}
        for r in fresh['references']:
            for span in r['premise_spans']+[r['target_span']]:
                self.assertEqual(lookup[r['sample_id']][span['source']][span['start']:span['end']],span['text'])

    def test_not_applicable_warrant_is_not_a_quality_failure(self):
        self.row['stage_status']={'proposal':'accepted','witness':'accepted','warrant':'not_applicable'}
        self.assertEqual(evaluate_rows([self.row],[])['stage_quality_failure_counts'],{})

    def test_identical_failures_do_not_count_as_stable_semantic_outputs(self):
        failed=dict(sample_id='x',status='witness_failed',annotation=None,stage_status={'witness':'quality_rejected'})
        out=compare_repeats([[failed],[failed]],[])
        self.assertFalse(out['whole_stage_equal'])
        self.assertEqual(out['expected_pairs'],1);self.assertEqual(out['completed_pairs'],0)

    def test_repeat_pair_completion_and_semantic_agreement_are_separate(self):
        out=compare_repeats([[self.row],[]],[])
        self.assertEqual(out['expected_pairs'],1);self.assertEqual(out['completed_pairs'],0)
        same=compare_repeats([[self.row],[self.row]],[])
        self.assertEqual(same['completed_pairs'],1);self.assertEqual(same['semantic_agreement'],1)

if __name__=='__main__':unittest.main()
