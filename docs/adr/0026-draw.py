"""The seeded draw (stratified: every sub-kind of a class once before any twice; no repeated element) for harness ADR-0026: 36 random edits over the enumerated surface of
kernels/cellchat.py, six per class. Reads the file by ast (no import of scprofile); prints the
list the ADR records before any change. Seed = 20260915."""
import ast, random, sys
src = open(sys.argv[1]).read()
d = ast.literal_eval(next(n for n in ast.parse(src).body
                          if isinstance(n, ast.Assign) and n.targets[0].id == 'PLUGIN').value)
figs = d['report']['figures']
ids = [f['id'] for f in figs]
with_at_most = [f['id'] for f in figs if 'at_most' in f]
with_fn = [f['id'] for f in figs if f.get('fn')]
with_args = [f['id'] for f in figs if f.get('args')]
tool_drawn = [f['id'] for f in figs if f.get('drawn_by') == 'tool']
skips = [k for k, v in d['report']['skips'].items() if v.get('skip') == 'over_budget']
AXES = ['sample', 'group', 'unit', 'contrast', 'interaction', 'cohort']
POSITIONS = ['overview', 'contrast', 'conclusion', 'appendix']
KINDS = ['diff_matrix', 'flow_compare', 'role_shift', 'circle', 'chord', 'matrix', 'role_scatter',
         'flow_rank', 'role_heatmap', 'contribution', 'unit_presence', 'unit_totals', 'interaction',
         'across_design']
HOST = ['across_design', 'unit_presence', 'unit_totals', 'interaction']
CFG = [k for k in d['config']]
PRODUCES = d['produces']
rng = random.Random(20260915)
ch = rng.choice
out = []

def m(cls, element, mutation, expect, reverse):
    if any(o[0] == cls and o[1] == element and o[2] == mutation for o in out):
        return False
    out.append((cls, element, mutation, expect, reverse))
    return True

def six(cls):
    return sum(1 for o in out if o[0] == cls) < 6

def kinds(options):
    """The sub-kinds of a class in a seeded order, each once before any twice."""
    order = rng.sample(options, len(options))
    while True:
        for k in order:
            yield k

# A: a value inside its domain
_kA = kinds(['at_most', 'axis', 'position', 'size', 'host_panels', 'config', 'cost_cores', 'legend'])
while six('A'):
    what = next(_kA)
    if what == 'at_most':
        e = ch(with_at_most); f = next(x for x in figs if x['id'] == e); new = f['at_most'] + ch([1, 2, -1]) or 1
        m('A', f'{e}.at_most', f'{f["at_most"]} -> {max(1,new)}', 'plan/layout count changes by the difference x occurrences; baseline refuses until re-recorded; the run draws exactly that many', 'set back')
    elif what == 'axis':
        e = ch(ids); f = next(x for x in figs if x['id'] == e); new = ch([a for a in AXES if a != f['axis']])
        m('A', f'{e}.axis', f'{f["axis"]} -> {new}', 'the family moves axis in plan and layout; the R guard and the profile list follow; the run files it under the new axis', 'set back')
    elif what == 'position':
        e = ch(ids); f = next(x for x in figs if x['id'] == e); new = ch([p for p in POSITIONS if p != f['position']])
        m('A', f'{e}.position', f'{f["position"]} -> {new}', 'the figure set moves the plate between main and supplementary; the section and legends renumber; nothing else changes', 'set back')
    elif what == 'size':
        e = ch([x['id'] for x in figs if 'w' in x]); f = next(x for x in figs if x['id'] == e)
        m('A', f'{e}.w,h', f'{f.get("w")}x{f.get("h")} -> {int(f.get("w")*1.5)}x{int((f.get("h") or f.get("w"))*1.5)}', 'the companion regenerates with the new device size; the run draws that size; no count changes', 'set back')
    elif what == 'host_panels':
        k = ch(HOST); m('A', 'report.host_panels', f'drop {k}', 'layout host count drops; the run draws none of that kind; the composed Methods and the figure set follow', 'add back')
    elif what == 'config':
        k = ch(CFG); m('A', f'config.{k}.default', 'another value in its domain', 'defaults stage re-reads; the reuse key changes; the cache key (if inference-side) changes and the run re-infers', 'set back')
    elif what == 'cost_cores':
        m('A', 'cores', '2 -> 4', 'the cores stage owes a measurement against a run; the wave plans 4 per instance', 'set back')
    else:
        e = ch(ids); m('A', f'{e}.legend', 'one sentence rewritten (same facts)', 'stated disclosures bound to the old words are reported as unbound BEFORE any run; the paper page prints the new legend', 'set back, or re-state')

# B: rename
_kB = kinds(['id', 'produces', 'config_key', 'subject'])
while six('B'):
    what = next(_kB)
    if what == 'id':
        e = ch(tool_drawn); m('B', f'{e}.id', f'{e} -> {e}_renamed', 'every site follows (R draw sites, profile list, evidence routes, skips, baseline); files carry the new name; one verb', 'rename back')
    elif what == 'produces':
        p = ch(PRODUCES); m('B', 'produces[...]', f'{p} -> a path the plugin does not write', 'the contract stage reads red against the last run; the run prints it as declared-not-emitted', 'set back')
    elif what == 'config_key':
        k = ch(CFG); m('B', f'config.{k}', f'{k} -> {k}_x', 'the code that reads C["{k}"] must follow or validate refuses; defaults stage re-reads', 'rename back')
    else:
        m('B', 'report.subject', 'cell-cell communication -> intercellular signalling', 'every composed title and the page title follow; nothing else', 'set back')

# C: add / remove / duplicate / reorder
_kC = kinds(['remove', 'add', 'duplicate', 'reorder', 'host_add', 'produces_remove'])
while six('C'):
    what = next(_kC)
    if what == 'remove':
        e = ch(ids); m('C', f'figures[{e}]', 'remove the entry', 'plan and layout counts drop; the R draw site and profile mark go; baseline refuses until re-recorded; the run draws exactly the rest', 'add back from the record')
    elif what == 'add':
        fn = ch(skips); m('C', 'figures[+]', f'add an entry drawing {fn} (from skips)', 'the skip is lifted; the plan counts it; layout may refuse over budget; the companion gains a draw site; the run draws it or the promise is refused', 'remove')
    elif what == 'duplicate':
        e = ch(ids); m('C', f'figures[{e}] x2', 'duplicate the entry under a new id', 'a twin family; layout counts twice; overfit/rules see duplicated mechanism', 'remove the twin')
    elif what == 'reorder':
        a, b = rng.sample(ids, 2); m('C', f'figures order', f'swap {a} and {b}', 'nothing changes but the figure-set order within a subject; the baseline holds', 'swap back')
    elif what == 'host_add':
        m('C', 'report.host_panels', 'add a kind the host implements but the plugin did not keep (e.g. role_shift)', 'layout host count rises; the run draws it per contrast', 'remove')
    else:
        p = ch(PRODUCES); m('C', 'produces', f'remove {p}', 'the contract stage says an emitted file is undeclared', 'add back')

# D: outside the domain
_kD = kinds(['kind', 'axis', 'r_arg', 'cohort_word', 'at_most0', 'dup_id', 'fn_unknown', 'position'])
while six('D'):
    what = next(_kD)
    e = ch(ids)
    if what == 'kind': m('D', f'{e}.kind', 'an id the host has no kind for', 'validate refuses by name before anything runs', 'set back')
    elif what == 'axis': m('D', f'{e}.axis', 'an axis the host lacks', 'validate refuses; layout refuses', 'set back')
    elif what == 'r_arg':
        e = ch(with_fn); m('D', f'{e}.args', 'an argument the R function does not take', 'a LOCAL check refuses it against the recorded formals of the wrapped tool; today only the run finds it', 'set back')
    elif what == 'cohort_word': m('D', f'{e}.legend', 'a cohort word in the legend', 'the portability suite refuses by name', 'set back')
    elif what == 'at_most0': m('D', f'{e}.at_most', '0', 'validate refuses; plan counts zero', 'set back')
    elif what == 'dup_id': m('D', 'figures', f'a second entry with id {e}', 'validate refuses the duplicate id', 'remove')
    elif what == 'fn_unknown': m('D', f'{e}.fn', 'a function the wrapped tool has not got', 'the inventory/account stage refuses against the upstream listing; the promise is refused on the run', 'set back')
    else: m('D', f'{e}.position', 'a position the set has no place for', 'validate refuses', 'set back')

# E: a missing key
_kE = kinds(['legend', 'axis', 'kind', 'state_version', 'host_panels', 'config_default', 'requires', 'version'])
while six('E'):
    what = next(_kE)
    e = ch(ids)
    m('E', {'legend': f'{e}.legend', 'axis': f'{e}.axis', 'kind': f'{e}.kind', 'state_version': 'state_version',
            'host_panels': 'report.host_panels', 'config_default': f'config.{ch(CFG)}.default', 'requires': 'requires.packages',
            'version': 'version'}[what], 'delete the key',
      {'legend': 'validate refuses: a kept entry without a legend', 'axis': 'validate refuses; plan cannot count it',
       'kind': 'validate refuses', 'state_version': 'validate refuses (already an ERROR)', 'host_panels': 'the host draws every kind again (undeclared = all); layout host count reads the default',
       'config_default': 'defaults stage refuses', 'requires': 'environment stage refuses', 'version': 'freshness refuses'}[what], 'restore')

# F: code-side
F = [('a `_fig_*` panel writes one extra file', 'promised/output-nobody-asked-for refuses the extra; the plan does not count it'),
     ('the generated companion edited by hand (one argument at a draw site)', '`generated` reads the companion stale before any run; scaffold --force rewrites it'),
     ('a comment inside the RECIPE span of the R inference', 'the cache stamp changes: the control run re-infers (18 x ~5 min) - the local state must SAY the cache will miss'),
     ('a plan change with the baseline not re-recorded', 'the baseline test refuses; the commit gate blocks'),
     ('a plan change with the version not bumped', 'freshness reads stale against the last run; the reuse key would collide'),
     ('an `expr` changed to another measure of the same function', 'no count changes; the promise holds; only the eye sees the difference - the stated disclosures of that kind are reported as at risk')]
for i in range(6):
    a, b = F[i]; m('F', 'code', a, b, 'git checkout of the file (not a hand edit)')

for n, (cls, el, mu, ex, rv) in enumerate(out, 1):
    print(f"| {n:2} | {cls} | `{el}` | {mu} | {ex} | {rv} |")
