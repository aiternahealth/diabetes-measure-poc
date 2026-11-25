"""Validate instance data (+ ontology for class hierarchy and value-set membership) against dcg-shapes.ttl."""
import sys, rdflib, pyshacl
data = rdflib.Graph().parse(sys.argv[1] if len(sys.argv) > 1 else 'scripts/shacl_sample.ttl')
data += rdflib.Graph().parse('ontology/dcg-ontology.ttl')
shapes = rdflib.Graph().parse('ontology/dcg-shapes.ttl')
conforms, rg, _ = pyshacl.validate(data, shacl_graph=shapes, inference='rdfs', allow_warnings=True)
SH = rdflib.Namespace('http://www.w3.org/ns/shacl#')
res = sorted((str(rg.value(r, SH.focusNode)).split('/')[-1], str(rg.value(r, SH.resultSeverity)).split('#')[-1], str(rg.value(r, SH.resultMessage)))
             for r in rg.subjects(rdflib.RDF.type, SH.ValidationResult))
for r in res: print(*r, sep=' | ')
print('conforms:', conforms, '| results:', len(res))
if len(sys.argv) == 1:   # self-test expectations for the sample file
    focus = {r[0] for r in res}
    assert not focus & {'P1', 'C1', 'A1'}, 'clean records were flagged'
    assert {'P2', 'C2', 'A2', 'B1'} <= focus, 'expected defects not detected'
    assert any('TemporalInconsistency' in r[2] for r in res), 'future date not detected'
    print('SHACL self-test: PASS')
