import copy
import unittest
from patterns_v2 import mine_patterns, retrieve as stable_retrieve, bootstrap_recovery


def retrieve(*args,**kwargs):
    """Structural tests opt out of the separate bootstrap acceptance gate."""
    kwargs.setdefault('min_bootstrap',0)
    return stable_retrieve(*args,**kwargs)


def fixture(article=0, label='Authority'):
    p={'unit':0,'first':0,'last':1,'owner':'current_author','speech_act':'assert','modality':'certain','polarity':'positive','event_role':'none','implicit':False,'gloss':''}
    a={'kind':'support','premises':[0,1],'target_kind':'proposition','target':2,'scheme':'testimony','stance':'uses','scope_change':'na','alternatives':'na','evidence':[{'unit':0,'first':0,'last':1}],'roles':[{'role':'source','proposition':0},{'role':'claim','proposition':2}]}
    return {'sample_id':str(article),'article_id':article,'gold':label,'split':'induction','status':'accepted','units':[{'id':0,'source':'comment','text':'one two three','start':0,'end':13}], 'annotation':{'propositions':[dict(p),dict(p),dict(p)],'applications':[a]},'graph':{'nodes':[],'edges':[]}}


class NativePatterns(unittest.TestCase):
    def test_unknown_bootstrap_cannot_claim_stable_retrieval(self):
        patterns=mine_patterns([fixture(i) for i in range(20)])
        self.assertEqual(len(stable_retrieve(patterns,fixture(99))),0)
        for p in patterns:p['bootstrap_recovery']=.9
        self.assertTrue(stable_retrieve(patterns,fixture(99)))

    def test_same_article_in_competing_labels_counts_as_counterevidence(self):
        rows=[fixture(i,label) for label in ['A','B'] for i in range(30)]
        self.assertEqual(len(mine_patterns(rows,min_purity=.75)),0)
        patterns=mine_patterns(rows,min_purity=.45)
        self.assertTrue(patterns)
        self.assertTrue(all(p['purity']==.5 and p['outside_label_articles']==30 for p in patterns))
        recovery=bootstrap_recovery(patterns,rows,rounds=3,min_purity=.75)
        self.assertTrue(all(value==0 for value in recovery.values()))
    def test_root_matches_inside_connected_extension(self):
        patterns=mine_patterns([fixture(i) for i in range(8)])
        row=fixture(99);tail=copy.deepcopy(row['annotation']['applications'][0])
        tail.update(premises=[2],target=1,scheme='evidence',roles=[])
        row['annotation']['applications'].append(tail)
        self.assertTrue(retrieve(patterns,row))

    def test_unordered_bindings_and_proposition_permutation(self):
        patterns=mine_patterns([fixture(i) for i in range(8)])
        row=fixture(99);a=row['annotation']['applications'][0]
        a['premises'].reverse();a['roles'].reverse()
        self.assertTrue(retrieve(patterns,row))
        permutation={0:2,1:0,2:1};old=row['annotation']['propositions']
        row['annotation']['propositions']=[old[1],old[2],old[0]]
        a['premises']=[permutation[p] for p in a['premises']];a['target']=permutation[a['target']]
        for r in a['roles']:r['proposition']=permutation[r['proposition']]
        candidates=retrieve(patterns,row)
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]['target_id'],1)
        self.assertEqual(set(candidates[0]['premise_proposition_ids']),{0,2})

    def test_opposite_direction_not_same_role_motif(self):
        patterns=mine_patterns([fixture(i) for i in range(8)])
        row=fixture(99);a=row['annotation']['applications'][0]
        a['premises']=[2,1];a['target']=0
        self.assertEqual(retrieve(patterns,row),[])

    def test_distinct_articles(self):
        self.assertEqual(mine_patterns([fixture(0) for _ in range(9)]),[])

    def test_topology_roles_and_mappings(self):
        rows=[fixture(i) for i in range(8)]
        patterns=mine_patterns(rows)
        self.assertTrue(patterns)
        candidate=retrieve(patterns,fixture(90))[0]
        self.assertEqual(candidate['premise_proposition_ids'],[0,1])
        self.assertEqual(candidate['target_id'],2)
        self.assertEqual(len(candidate['mapping']),4)
        changed=fixture(91);changed['annotation']['applications'][0]['premises']=[0]
        self.assertEqual(retrieve(patterns,changed),[])
        changed=fixture(92);changed['annotation']['applications'][0]['roles'][0]['role']='sample'
        self.assertEqual(retrieve(patterns,changed),[])

    def test_recovery_and_prototypes(self):
        rows=[fixture(i) for i in range(30)]
        patterns=mine_patterns(rows)
        recovery=bootstrap_recovery(patterns,rows,rounds=10)
        self.assertEqual(recovery[patterns[0]['id']],1)
        self.assertTrue(patterns[0]['prototypes'])
        self.assertEqual(patterns[0]['merged_graph']['composition'],'alternative_prototypes')

    def test_application_target_is_preserved(self):
        rows=[fixture(i) for i in range(6)]
        for row in rows:
            a=copy.deepcopy(row['annotation']['applications'][0]);a.update(kind='undercut',premises=[2],target_kind='application',target=0)
            row['annotation']['applications'].append(a)
        patterns=mine_patterns(rows)
        cs=retrieve(patterns,rows[0],top_k=10)
        self.assertTrue(any(p['constraints']['kind']=='undercut' for p in patterns))
        under=next(p for p in patterns if p['constraints']['kind']=='undercut')
        self.assertGreater(len(under['prototypes'][0]['graph']['nodes']),4)

    def test_bootstrap_gate_and_top_three_labels(self):
        rows=[fixture(i,label) for i,label in enumerate(['A']*8+['B']*8+['C']*8+['D']*8)]
        patterns=mine_patterns(rows,min_purity=.2)
        self.assertEqual(len(retrieve(patterns,fixture(90))),3)
        for p in patterns:p['bootstrap_recovery']=.79
        self.assertEqual(retrieve(patterns,fixture(90),min_bootstrap=.8),[])

    def test_compiled_spans_and_semantic_objects_preserved(self):
        from ontology_v2 import compile_graph
        rows=[fixture(i) for i in range(8)]
        for r in rows:r['graph']=compile_graph(r['annotation'],r['units'])
        c=retrieve(mine_patterns(rows),rows[0])[0]
        types={n['type'] for n in c['source_graph']['nodes']}
        self.assertTrue({'SourceSpan','Assertion','Proposition','SchemeHypothesis','InferenceApplication'}<=types)
        span=next(n for n in c['source_graph']['nodes'] if n['type']=='SourceSpan')
        self.assertEqual(span['text'],'one')

    def test_prototypes_cannot_invent_a_cross_path(self):
        rows=[fixture(i) for i in range(12)]
        for r in rows[6:]:
            r['annotation']['applications'][0]['premises']=[1]
        patterns=mine_patterns(rows)
        self.assertEqual(len(patterns),2)
        for pattern in patterns:
            self.assertEqual(len(pattern['merged_graph']['prototypes']),1)
            graph=pattern['prototypes'][0]['graph']
            count=sum(e['rel']=='PREMISE_OF' for e in graph['edges'])
            self.assertIn(count,[1,2])


    def test_same_label_retains_distinct_subgraph_candidates_for_verifier(self):
        patterns=mine_patterns([fixture(i) for i in range(8)])
        row=fixture(99);row['annotation']['propositions']=[dict(p,first=j,last=j+1) for j,p in enumerate(row['annotation']['propositions']*2)]
        row['units'][0].update(text='one two three four five six',end=len('one two three four five six'))
        other=copy.deepcopy(row['annotation']['applications'][0]);other.update(premises=[3,4],target=5,roles=[dict(role='source',proposition=3),dict(role='claim',proposition=5)])
        row['annotation']['applications'].append(other)
        candidates=retrieve(patterns,row)
        self.assertEqual({c['target_id'] for c in candidates},{2,5})
        self.assertEqual(len({c['id'] for c in candidates}),2)
        from ontology_v2 import compile_graph
        row['graph']=compile_graph(row['annotation'],row['units'])
        candidates=retrieve(patterns,row)
        second=next(c for c in candidates if c['target_id']==5)
        self.assertTrue(any(n.get('type')=='SourceSpan' and n.get('text')=='six' for n in second['source_graph']['nodes']))

    def test_candidate_budget_preserves_label_diversity_and_per_label_alternatives(self):
        patterns=mine_patterns([fixture(i,label) for i,label in enumerate(['A']*8+['B']*8+['C']*8+['D']*8)],min_purity=.2)
        row=fixture(99);row['annotation']['propositions']=[dict(p,first=j,last=j+1) for j,p in enumerate(row['annotation']['propositions']*2)]
        row['units'][0].update(text='one two three four five six',end=len('one two three four five six'))
        other=copy.deepcopy(row['annotation']['applications'][0]);other.update(premises=[3,4],target=5,roles=[dict(role='source',proposition=3),dict(role='claim',proposition=5)])
        row['annotation']['applications'].append(other)
        candidates=retrieve(patterns,row,top_k=3,max_per_label=2)
        self.assertEqual(len(candidates),6);self.assertEqual(len({c['label'] for c in candidates}),3)

    def test_concessions_are_preserved_in_source_but_do_not_become_fallacy_cores(self):
        rows=[fixture(i) for i in range(8)]
        for row in rows:row['annotation']['applications'][0].update(kind='concession',scheme='other',roles=[])
        self.assertEqual(len(mine_patterns(rows)),0)

    def adoption_rows(self):
        from ontology_v2 import source_units,compile_graph
        units=source_units(dict(comment="Yes, that's right. We must allow criticism.",parent_comment='Silencing critics harms debate.'))
        base=dict(owner='current_author',speech_act='assert',modality='certain',polarity='positive',event_role='none',implicit=False,gloss='')
        ps=[dict(base,unit=0,first=0,last=3),dict(base,unit=1,first=0,last=4,speech_act='recommend'),dict(base,unit=2,first=0,last=4,owner='parent_author')]
        apps=[dict(kind='adoption',premises=[0],target_kind='proposition',target=2,scheme='other',stance='uses',scope_change='na',alternatives='na',roles=[dict(role='adoption_cue',proposition=0)],evidence=[dict(unit=0,first=0,last=3)]),dict(kind='support',premises=[2],target_kind='proposition',target=1,scheme='evidence',stance='uses',scope_change='na',alternatives='na',roles=[],evidence=[dict(unit=2,first=0,last=4)])]
        a=dict(propositions=ps,applications=apps)
        return [dict(sample_id=str(i),article_id=i,gold='Example',split='induction',status='accepted',units=units,annotation=copy.deepcopy(a),graph=compile_graph(a,units)) for i in range(8)]

    def test_adoption_reference_is_not_learned_as_an_argumentative_core(self):
        patterns=mine_patterns(self.adoption_rows())
        self.assertEqual({p['constraints']['kind'] for p in patterns},{'support'})

    def test_context_candidate_preserves_its_actual_adoption_and_endorsement(self):
        rows=self.adoption_rows();patterns=mine_patterns(rows)
        c=next(c for c in retrieve(patterns,rows[0]) if c['kind']=='support')
        g=c['source_graph']
        self.assertTrue(any(e['type']=='ADOPTS' and e['target']=='p2' for e in g['edges']))
        self.assertTrue(any(n['id']=='p0' and n['type']=='Proposition' for n in g['nodes']))
        self.assertTrue(any(n['type']=='SourceSpan' and n['text']=="Yes, that's right." for n in g['nodes']))

if __name__=='__main__':unittest.main()
