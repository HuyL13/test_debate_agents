"""Neutral, synthetic source examples; no dataset label or evaluation source."""
from ontology_v2 import source_units
from source_quotes_v2 import quote_source_payload,readable_propositions
from decomposed_source_v2 import prepare_propositions,bind_relations


def examples():
    specs=[
        ('Age alone does not justify preserving a rule. We should assess its effects instead.',[
            (0,'Age alone does not justify preserving a rule.','current_author','assert','unspecified','negative',False,''),
            (0,'Age alone does not justify preserving a rule.','unclear','hypothetical','unspecified','positive',True,'The rule is old.'),
            (0,'Age alone does not justify preserving a rule.','unclear','recommend','unspecified','positive',True,'The rule should be preserved.'),
            (1,'We should assess its effects instead.','current_author','recommend','unspecified','positive',False,'')],
            [dict(id='a0',kind='support',premises=['p1'],target_kind='proposition',target='p2',stance='critiques',roles=[],evidence_units=[0]),dict(id='a1',kind='undercut',premises=['p0'],target_kind='application',target='a0',stance='uses',roles=[],evidence_units=[0])]),
        ('Officials should be allowed to hide abusive replies. This could lead to hiding legitimate criticism. We should protect open debate.',[
            (0,'Officials should be allowed to hide abusive replies.','current_author','recommend','unspecified','positive',False,''),
            (1,'This could lead to hiding legitimate criticism.','current_author','hypothetical','possible','positive',False,''),
            (2,'We should protect open debate.','current_author','recommend','unspecified','positive',False,'')],
            [dict(id='a0',kind='projection',premises=['p0'],target_kind='proposition',target='p1',stance='uses',roles=[],evidence_units=[1]),dict(id='a1',kind='support',premises=['p1'],target_kind='proposition',target='p2',stance='uses',roles=[],evidence_units=[1,2])])]
    specs.extend([
        ('I value custom. Nevertheless I support changing the rule. It harms people.',[
            (0,'I value custom.','current_author','assert','certain','positive',False,''),
            (1,'Nevertheless I support changing the rule.','current_author','recommend','unspecified','positive',False,''),
            (2,'It harms people.','current_author','assert','certain','positive',False,'')],
            [dict(id='a0',kind='concession',premises=['p0'],target_kind='proposition',target='p1',stance='uses',roles=[],evidence_units=[0,1]),dict(id='a1',kind='support',premises=['p2'],target_kind='proposition',target='p1',stance='uses',roles=[],evidence_units=[2])]),
        ('There are only two options: adopt the draft or abandon the project. Therefore we must adopt the draft.',[
            (0,'There are only two options: adopt the draft or abandon the project.','current_author','assert','certain','positive',False,''),
            (0,'adopt the draft','current_author','hypothetical','unspecified','positive',False,''),
            (0,'abandon the project.','current_author','hypothetical','unspecified','positive',False,''),
            (1,'Therefore we must adopt the draft.','current_author','recommend','unspecified','positive',False,'')],
            [dict(id='a0',kind='support',premises=['p0'],target_kind='proposition',target='p3',stance='uses',roles=[dict(role='choice',proposition='p1'),dict(role='choice',proposition='p2')],evidence_units=[0,1])]),
        ('The poster promises every room is quiet. Guests report noisy rooms. That makes the promise doubtful.',[
            (0,'The poster promises every room is quiet.','attributed','report','certain','positive',False,''),
            (1,'Guests report noisy rooms.','attributed','report','unspecified','positive',False,''),
            (2,'That makes the promise doubtful.','current_author','assert','unspecified','positive',False,'')],
            [dict(id='a0',kind='rebut',premises=['p1'],target_kind='proposition',target='p0',stance='uses',roles=[],evidence_units=[0,1]),dict(id='a1',kind='support',premises=['p0','p1'],target_kind='proposition',target='p2',stance='uses',roles=[],evidence_units=[0,1,2])])])
    out=[]
    for text,props,apps in specs:
        sample=dict(comment=text,title='',parent_comment='');units=source_units(sample)
        raw={'propositions':[dict(unit=u,quote=q,owner=owner,speech_act=act,modality=modal,polarity=polarity,event_role='none',implicit=implicit,gloss=gloss) for u,q,owner,act,modal,polarity,implicit,gloss in props]}
        ps=prepare_propositions(raw,units);relations={'applications':apps};annotation=bind_relations(relations,ps,units)
        out.append(dict(source=quote_source_payload(sample,units),proposition_output=raw,relation_input=[{k:v for k,v in p.items() if k!='event_role'} for p in readable_propositions(dict(propositions=ps,applications=[]),units)],relation_output=relations,annotation=annotation,units=units))
    return out
