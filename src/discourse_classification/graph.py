import re

ONTOLOGY = ('SUPPORT', 'CAUSE', 'CONSEQUENCE', 'CONDITION', 'CONTRAST', 'ALTERNATIVE',
            'COMPARISON', 'GENERALIZATION', 'EXAMPLE', 'ELABORATION', 'JUSTIFICATION', 'TEMPORAL', 'SEQUENCE')
CONNECTIVES = {
    'because': 'JUSTIFICATION', 'therefore': 'CONSEQUENCE', 'thus': 'CONSEQUENCE',
    'but': 'CONTRAST', 'however': 'CONTRAST', 'although': 'CONTRAST',
    'or': 'ALTERNATIVE', 'if': 'CONDITION', 'then': 'CONSEQUENCE', 'until': 'SEQUENCE',
}

ORPHAN = re.compile(r'^(?:(?:and|but|or|if|then|because|although|however|until|though|so)[\s,;:]*)+$', re.I)
CAUSAL = r'(?:lead(?:s|ing)?\s+to|result(?:s|ing)?\s+in|cause(?:s)?|end\s+up)'


def choice_construction(text):
    if not re.search(r'\bor\b', text, re.I):
        return False
    if re.search(r'\beither\b|\b(?:only|two)\s+(?:possible\s+)?(?:choices|options|solutions|situations)\b', text, re.I):
        return True
    left, right = re.split(r'\bor\b', text, maxsplit=1, flags=re.I)
    predicate = r'\b(?:must|should|will|can|would|could|is|are|be|do|allow|ban|cut|accept|reject|choose|stop)\b'
    return bool(re.search(predicate, left, re.I) and re.search(predicate, right, re.I))


def merge_orphans(nodes, text):
    i = 0
    while i < len(nodes):
        node = nodes[i]
        if not any(c.isalnum() for c in node['text']):
            if i and nodes[i-1]['sentence_id'] == node['sentence_id']:
                nodes[i-1]['char_end'] = node['char_end']
                nodes[i-1]['text'] = text[nodes[i-1]['char_start']:node['char_end']]
                nodes.pop(i)
                continue
            if i+1 < len(nodes) and nodes[i+1]['sentence_id'] == node['sentence_id']:
                nodes[i+1]['char_start'] = node['char_start']
                nodes[i+1]['text'] = text[node['char_start']:nodes[i+1]['char_end']]
            nodes.pop(i)
            continue
        if ORPHAN.fullmatch(node['text'].strip(' .!?')) or re.fullmatch(
                r'not only that(?:\s+but)?', node['text'].strip(' .!?,;:'), re.I):
            if i+1 < len(nodes) and nodes[i+1]['sentence_id'] == node['sentence_id']:
                nodes[i+1]['char_start'] = node['char_start']
                nodes[i+1]['text'] = text[node['char_start']:nodes[i+1]['char_end']]
                nodes.pop(i)
                continue
            if i and nodes[i-1]['sentence_id'] == node['sentence_id']:
                nodes[i-1]['char_end'] = node['char_end']
                nodes[i-1]['text'] = text[nodes[i-1]['char_start']:node['char_end']]
                nodes.pop(i)
                continue
            # A stand-alone connective carries no proposition; keep source text in the original input.
            nodes.pop(i)
            continue
        if i and node['sentence_id'] == nodes[i-1]['sentence_id'] and re.match(r'or\b', node['text'], re.I) and not choice_construction(
                nodes[i-1]['text'] + ' ' + node['text']):
            previous = nodes[i-1]
            previous['char_end'] = node['char_end']
            previous['text'] = text[previous['char_start']:previous['char_end']]
            nodes.pop(i)
            continue
        i += 1


class StanzaParser:
    def __init__(self, model_dir):
        import stanza
        self.nlp = stanza.Pipeline('en', dir=str(model_dir),
            processors='tokenize,pos,lemma,depparse,constituency', verbose=False,
            download_method=None, use_gpu=False)

    def __call__(self, text):
        doc = self.nlp(text)
        spans = []
        for sid, sentence in enumerate(doc.sentences):
            tokens = sentence.tokens
            cuts = {tokens[0].start_char, tokens[-1].end_char}
            words = {w.id: w for w in sentence.words}
            positions = {w.id: t.start_char for t in tokens for w in t.words}
            # Clause markers qualify only when attached to a predicate, avoiding noun coordination.
            for word in sentence.words:
                head = words.get(word.head)
                if word.deprel in ('mark', 'cc') and head and head.upos in ('VERB', 'AUX', 'ADJ'):
                    if word.text.lower() in CONNECTIVES or word.text.lower() in ('since', 'while', 'as', 'so'):
                        cuts.add(positions[word.id])
            # Constituency leaves map to word offsets; nested S/SBAR boundaries supplement dependencies.
            def walk(tree, index=0, parent=None):
                if not tree.children:
                    return index + 1
                start = index
                for child in tree.children:
                    index = walk(child, index, tree.label)
                labels = {child.label for child in tree.children}
                finite = any(w.upos in ('VERB', 'AUX') and w.feats and 'VerbForm=Fin' in w.feats
                             for w in sentence.words[start:index])
                discourse_clause = tree.label == 'SBAR' and sentence.words[start].text.lower() in {
                    *CONNECTIVES, 'since', 'while', 'as', 'so', 'unless', 'until', 'after', 'before'}
                coordinated = start > 0 and sentence.words[start-1].upos == 'CCONJ'
                meaningful = discourse_clause or (tree.label in ('S', 'SINV') and
                    parent != 'SBAR' and coordinated and 'NP' in labels and 'VP' in labels and finite)
                if meaningful and start > 0 and start + 1 in positions:
                    cuts.add(positions[start + 1])
                if discourse_clause and start == 0 and index + 1 in positions:
                    cuts.add(positions[index + 1])
                return index
            walk(sentence.constituency)
            boundaries = sorted(cuts)
            spans.extend((a, b, sid) for a, b in zip(boundaries, boundaries[1:]))
        return spans


def build_graph(text, parser=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Comment must be nonempty')
    spans = parser(text) if parser else [(m.start(), m.end(), i) for i, m in enumerate(re.finditer(r'[^.!?]+[.!?]*', text))]
    nodes = []
    for a, b, sid in spans:
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b-1].isspace():
            b -= 1
        if a < b:
            nodes.append({'id': f'P{len(nodes)+1}', 'text': text[a:b], 'char_start': a, 'char_end': b, 'sentence_id': sid})
    merge_orphans(nodes, text)
    graph = {'propositions': nodes, 'relations': [], 'edges': []}
    # Constructions may occur inside one clause; split exact spans only at a qualified connective.
    for node in list(nodes):
        match = re.search(r'\b(because|therefore|thus|but|however|although|or|if|then|until)\b', node['text'], re.I)
        if not match or match.start() == 0:
            continue
        left, right = node['text'][:match.start()], node['text'][match.end():]
        if not left.strip() or not right.strip():
            continue
        # "or" can join nominal alternatives: retain as a broad candidate, not a verified relation.
        if match.group().lower() == 'or' and not choice_construction(node['text']):
            continue
        idx = nodes.index(node)
        boundary = node['char_start'] + match.start()
        end_left = boundary
        while text[end_left-1].isspace():
            end_left -= 1
        node['char_end'], node['text'] = end_left, text[node['char_start']:end_left]
        start_right = boundary
        original_end = node['char_start'] + len(left) + len(match.group()) + len(right)
        nodes.insert(idx+1, {'id': '', 'text': text[start_right:original_end], 'char_start': start_right,
                             'char_end': original_end, 'sentence_id': node['sentence_id']})
    merge_orphans(nodes, text)
    for i, n in enumerate(nodes):
        n['id'] = f'P{i+1}'
    for i, n in enumerate(nodes):
        cue = re.match(r'(?:(?:and|but)\s+)?(because|if)\b', n['text'], re.I) or re.match(
            r'(because|therefore|thus|but|however|although|or|if|then|until)\b', n['text'], re.I)
        if cue and cue.group(1).lower() in ('because', 'if'):
            kind = 'JUSTIFICATION' if cue.group(1).lower() == 'because' else 'CONDITION'
            preceding = [p for p in nodes[:i] if p['sentence_id'] == n['sentence_id']]
            # Postposed clauses point back to the main clause; coordinated reasons share it.
            targets = [p for p in preceding if not re.match(r'(?:and\s+)?(?:because|if)\b', p['text'], re.I)
                       and p['text'].strip(' ,;').lower() != 'and']
            if targets:
                target = targets[-1]
                add_relation(graph, kind, n['id'], target['id'], 'explicit', cue.group(1))
            elif i + 1 < len(nodes) and nodes[i+1]['sentence_id'] == n['sentence_id']:
                add_relation(graph, kind, n['id'], nodes[i+1]['id'], 'explicit', cue.group(1))
        elif i and cue:
            relation = CONNECTIVES[cue.group(1).lower()]
            if cue.group(1).lower() == 'until' and re.match(r'until\s+(?:recently|now|today|yesterday)\b', n['text'], re.I):
                relation = 'TEMPORAL'
            a, b = nodes[i-1]['id'], n['id']
            if relation != 'ALTERNATIVE' or choice_construction(nodes[i-1]['text'] + ' ' + n['text']):
                add_relation(graph, relation, a, b, 'explicit', cue.group(1))
        if i and re.search(r'\b(more|worse|better|less)\b.*\b(than|urgent|important|serious)\b', n['text'], re.I):
            add_relation(graph, 'COMPARISON', nodes[i-1]['id'], n['id'], 'explicit', '')
        if i and re.search(r'\b(?:bigger|greater|worse|smaller)\s+(?:issues|problems|threats)\b', n['text'], re.I):
            add_relation(graph, 'COMPARISON', nodes[i-1]['id'], n['id'], 'explicit', 'severity comparison')
        if i and re.search(r'\binstead\b', n['text'], re.I):
            previous = nodes[i-1]
            if i > 1 and re.match(r'Not even\b', previous['text'], re.I):
                previous = nodes[i-2]
            add_relation(graph, 'CONTRAST', previous['id'], n['id'], 'explicit', 'instead')
        if i and re.search(r'\b' + CAUSAL + r'\b', n['text'], re.I) and re.match(
                r'(?:(?:though|but|however)\s+)?(?:it|this|that)\b', n['text'], re.I):
            add_relation(graph, 'CAUSE', nodes[i-1]['id'], n['id'], 'explicit', 'causal construction')
        if i and (n['text'].rstrip().endswith('?') or re.match(r'(?:will|would|could)\b', n['text'], re.I)) and nodes[i-1]['text'].rstrip().endswith('?') and re.search(
                r'\b(next|after|then|will|would)\b', n['text'], re.I):
            add_relation(graph, 'SEQUENCE', nodes[i-1]['id'], n['id'], 'explicit', 'question sequence')
        if i and nodes[i-1]['text'].rstrip().endswith('and') and re.search(r'\bwill\b', n['text'], re.I) and (
                re.match(r'until\b', nodes[i-1]['text'], re.I) or
                any(r['type'] in ('SEQUENCE', 'CONSEQUENCE') and r['arg2'] == nodes[i-1]['id'] for r in graph['relations'])):
            add_relation(graph, 'SEQUENCE', nodes[i-1]['id'], n['id'], 'explicit', 'coordinated future consequence')
    return graph


def add_relation(graph, kind, a, b, source, cue=''):
    if kind not in ONTOLOGY or a == b:
        raise ValueError('Invalid discourse relation')
    rid = f'R{len(graph["relations"])+1}'
    graph['relations'].append({'id': rid, 'type': kind, 'arg1': a, 'arg2': b, 'source': source, 'cue': cue})
    roles = ('MEMBER', 'MEMBER') if kind == 'ALTERNATIVE' else ('ARG1', 'ARG2')
    graph['edges'].extend([{'source': a, 'target': rid, 'role': roles[0]}, {'source': b, 'target': rid, 'role': roles[1]}])
