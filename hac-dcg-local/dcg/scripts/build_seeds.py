"""Derive seeds/seed_code_valueset.csv from the ontology so value sets have one source of truth.

Each row is one governed code map: source code -> value set, with the governance fields the DCI
mapping rules ask for (match type, SKOS relation, confidence, status, map version). ICD-10-CA rows
are prefix matches (the code and all its children)."""
import csv, sys, rdflib
from rdflib.namespace import SKOS, RDF, OWL
root = sys.argv[1] if len(sys.argv) > 1 else '.'
g = rdflib.Graph().parse(f'{root}/ontology/dcg-ontology.ttl')
DCG = 'https://ontology.hac-poc.example/dcg#'
D = lambda p: rdflib.URIRef(DCG + p)
SYS = {'http://snomed.info/id/': 'http://snomed.info/sct', 'http://loinc.org/rdf/': 'http://loinc.org',
       'http://www.whocc.no/atc/': 'http://www.whocc.no/atc',
       'https://fhir.infoway-inforoute.ca/CodeSystem/icd10ca/': 'https://fhir.infoway-inforoute.ca/CodeSystem/icd10ca'}
MAP_VERSION = str(g.value(rdflib.URIRef('https://ontology.hac-poc.example/dcg'), OWL.versionInfo))
rows = []
for c in g.subjects(RDF.type, SKOS.Concept):
    cs = str(c)
    system = next((v for k, v in SYS.items() if cs.startswith(k)), None)
    if not system: continue
    val = lambda p, d: str(g.value(c, D(p)) or d)  # noqa: E731
    default_match = 'prefix' if 'icd10ca' in system or 'atc' in system else 'exact'
    for vs in g.objects(c, SKOS.inScheme):
        rows.append((system, str(g.value(c, SKOS.notation)), str(vs).replace(DCG, ''), str(g.value(c, SKOS.prefLabel)),
                     val('matchType', default_match), val('mapRelation', 'exactMatch'), val('mapConfidence', 'high'),
                     val('mapStatus', 'candidate'), MAP_VERSION))
rows.sort()
with open(f'{root}/seeds/seed_code_valueset.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['code_system', 'code', 'value_set', 'display', 'match_type', 'map_relation', 'map_confidence', 'map_status', 'map_version'])
    w.writerows(rows)
print(len(rows), 'value-set rows, map version', MAP_VERSION)
