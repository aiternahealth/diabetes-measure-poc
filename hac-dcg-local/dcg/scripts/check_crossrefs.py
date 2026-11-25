"""Cross-layer consistency: ontology <-> semantic model <-> marts <-> views."""
import json, re, glob, sys, yaml, rdflib
from rdflib.namespace import RDF
DCG = 'https://ontology.hac-poc.example/dcg#'
g = rdflib.Graph().parse('ontology/dcg-ontology.ttl')
iris = {str(s).replace(DCG, 'dcg:') for s in g.subjects() if str(s).startswith(DCG)}
sm = yaml.safe_load(open('models/semantic/dcg_semantic_model.yml'))
metrics = {m['name'] for m in sm['metrics']}
measures = {ms['name'] for s in sm['semantic_models'] for ms in s['measures']}
dims = {d['name'] for s in sm['semantic_models'] for d in s['dimensions']}
errs = []
# 1. every ontology IRI cited in YAML exists
for v in re.findall(r'dcg:[A-Za-z0-9_]+', open('models/semantic/dcg_semantic_model.yml').read()):
    if v not in iris: errs.append(f'YAML cites unknown IRI {v}')
# 2. ontology semanticModelRef targets exist
for s, o in g.subject_objects(rdflib.URIRef(DCG + 'semanticModelRef')):
    for ref in str(o).split(','):
        kind, _, name = ref.strip().partition(':')
        pool = {'metric': metrics, 'measure': measures, 'dim': dims}.get(kind)
        if pool is None or name.endswith('*'): continue
        if name not in pool: errs.append(f'{s} semanticModelRef {ref.strip()} not in semantic model')
# 3. ontology indicators' metricName exist
for s, o in g.subject_objects(rdflib.URIRef(DCG + 'metricName')):
    if str(o) not in metrics: errs.append(f'{s} metricName {o} not a metric')
# 4. ratio/derived metric inputs exist (measures auto-create metrics)
allm = metrics | measures
for m in sm['metrics']:
    tp = m['type_params']
    for k in ('numerator', 'denominator', 'measure'):
        if k in tp and tp[k] not in allm: errs.append(f"{m['name']} {k} {tp[k]} undefined")
    for x in tp.get('metrics', []):
        if x['name'] not in allm: errs.append(f"{m['name']} uses undefined {x['name']}")
# 5. measure/dimension columns exist in mart SQL output
mart = ''.join(open(f).read() for f in glob.glob('models/marts/*.sql') + glob.glob('models/intermediate/*.sql'))
for s in sm['semantic_models']:
    for x in s['measures'] + s['dimensions']:
        for col in re.findall(r'[a-z_][a-z0-9_]*', re.sub(r"'[^']*'", '', x.get('expr', x['name']))):
            if col in ('case','when','then','else','end','and','or','as','varchar','cast','yes','no'): continue
            if col not in mart: errs.append(f"{s['name']}.{x['name']} references column {col} not in marts")
# 6. view columns referenced by marts exist in ViewDefinitions
viewcols = {}
for f in glob.glob('views/*.json'):
    v = json.load(open(f)); cols = set()
    for sel in v['select']: cols |= {c['name'] for c in sel.get('column', [])}
    viewcols[v['name']] = cols
checked = 0
for mf in glob.glob('models/marts/*.sql') + glob.glob('models/intermediate/*.sql'):
    sql = open(mf).read()
    for vname, cols in viewcols.items():
        for alias_use in re.findall(r"ref\('%s'\)\s*\}\}\s+(\w+)" % vname, sql):
            for col in set(re.findall(r'\b%s\.(\w+)' % alias_use, sql)):
                checked += 1
                if col not in cols: errs.append(f'{mf} uses {alias_use}.{col} not in view {vname}')
# 7. agent contract parses, and its tools match the MCP server's tools
contract = yaml.safe_load(open('agent/dcg_agent_contract.yaml'))
server_tools = set(re.findall(r'@mcp\.tool\(\)\ndef (\w+)', open('../agent/mcp_server.py').read()))
contract_tools = {t['name'] for t in contract['tools']}
if server_tools != contract_tools: errs.append(f'contract tools {sorted(contract_tools ^ server_tools)} differ from MCP server')
# 8. competency questions name governed metrics and dimensions
for q in yaml.safe_load(open('agent/competency_questions.yaml'))['questions']:
    for qq in q.get('queries', []):
        for x in qq['metrics']:
            if x not in metrics | measures: errs.append(f"{q['id']} unknown metric {x}")
        for x in qq.get('group_by', []):
            if x not in dims: errs.append(f"{q['id']} unknown dimension {x}")
print(checked, 'view-column references checked')
print('\n'.join(errs) if errs else 'all cross-references OK'); sys.exit(1 if errs else 0)
