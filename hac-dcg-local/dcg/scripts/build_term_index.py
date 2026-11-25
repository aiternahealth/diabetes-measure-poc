"""Builds agent/term_index.json: every synonym -> metric / dimension / ontology class."""
import json, yaml, rdflib
from rdflib.namespace import SKOS, RDFS, RDF, OWL
g = rdflib.Graph().parse('ontology/dcg-ontology.ttl')
DCG = 'https://ontology.hac-poc.example/dcg#'
q = lambda u: str(u).replace(DCG, 'dcg:')
idx = {}
def add(term, entry):
    lst = idx.setdefault(term.lower().strip(), [])
    if entry not in lst: lst.append(entry)
for c in set(g.subjects(RDF.type, OWL.Class)):
    if not str(c).startswith(DCG): continue
    ref = g.value(c, rdflib.URIRef(DCG + 'semanticModelRef'))
    e = {'kind': 'class', 'iri': q(c), 'semantic_model_ref': str(ref) if ref else None}
    for l in list(g.objects(c, RDFS.label)) + list(g.objects(c, SKOS.altLabel)): add(str(l), e)
sm = yaml.safe_load(open('models/semantic/dcg_semantic_model.yml'))
for m in sm['metrics']:
    e = {'kind': 'metric', 'name': m['name'], 'label': m['label']}
    add(m['label'], e); add(m['name'].replace('_', ' '), e)
    for s in m.get('config', {}).get('meta', {}).get('synonyms', []): add(s, e)
for s in sm['semantic_models']:
    ent = s['entities'][0]['name']
    for d in s['dimensions']:
        e = {'kind': 'dimension', 'name': f"{ent}__{d['name']}"}
        add(d['name'].replace('_', ' '), e)
        for syn in d.get('config', {}).get('meta', {}).get('synonyms', []): add(syn, e)
json.dump(dict(sorted(idx.items())), open('agent/term_index.json', 'w'), indent=1)
print(len(idx), 'terms indexed')
