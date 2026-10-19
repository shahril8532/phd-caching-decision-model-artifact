"""Model-attributed eager-load scan (artifact v1.4.0).

Counts, for every Eloquent relationship in a system's relationship inventory, the call sites in the
application's own code (app/, routes/, resources/views/) where that relationship is eager-loaded through
with(), load() or loadMissing(). Each call is attributed to the model on which it is made: class roots
(Model::with), variables (resolved through their assignment, foreach source or type hint), relation-method
and property chains (e.g. $user->pegawai()->with(...)), the authenticated user (Auth::user(),
auth()->user(), $request->user()), and nested paths such as 'pegawai.pkg', which count once for each
(model, relationship) pair they load. Non-Eloquent with() calls (redirect(), back(), view(), mailables,
console kernel) are ignored. Column selections ('rel:id,name') are reduced to the relationship name.

The source code of the three case-study systems is not part of this artifact; the script is included so
that the counting rules are explicit. Its output for the three systems is in data/eager_load/.

Usage:
  python3 eager_load_scan.py --system iTeams --source /path/to/iteams \
      --inventory ../data/relationship_inventories/iTeams_relationship_inventory.csv --method-col "Method Name"
"""
import re, os, csv, json, sys
BASES = {}      # system -> source directory, set from the command line
INVENTORY = {}  # system -> (inventory CSV path, method column name)
NONMODEL_FUNCS = {'redirect', 'back', 'view', 'response', 'session', 'request', 'collect', 'now', 'cache'}

def load_rel(system):
    m = {}
    path, mcol = INVENTORY[system]
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        if not r.get('Relationship Type'): continue
        m[(r['Source Model'].lower(), r[mcol].lower())] = (r['Source Model'], r[mcol], r['Related Model'])
    return m

def strip_php(s):
    out = []; i = 0; n = len(s); q = None
    while i < n:
        c = s[i]
        if q:
            out.append(c)
            if c == '\\' and i + 1 < n: out.append(s[i + 1]); i += 2; continue
            if c == q: q = None
            i += 1; continue
        if c in "'\"": q = c; out.append(c); i += 1; continue
        if s.startswith('//', i) or c == '#':
            j = s.find('\n', i); j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j; continue
        if s.startswith('/*', i):
            j = s.find('*/', i + 2); j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', s[i:j])); i = j; continue
        out.append(c); i += 1
    return ''.join(out)

def strip_blade(s):
    s = re.sub(r'\{\{--.*?--\}\}', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), s, flags=re.S)
    return s

def match_fwd(s, i, o='(', c=')'):
    d = 0; q = None
    for j in range(i, len(s)):
        ch = s[j]
        if q:
            if ch == '\\': continue
            if ch == q: q = None
            continue
        if ch in "'\"": q = ch
        elif ch in '([{': d += 1
        elif ch in ')]}':
            d -= 1
            if d == 0: return j
    return len(s) - 1

def match_back(s, j):
    d = 0; q = None
    for i in range(j, -1, -1):
        ch = s[i]
        if ch in ')]}': d += 1
        elif ch in '([{':
            d -= 1
            if d == 0: return i
    return 0

def split_top(s):
    """split s at depth-0 commas"""
    parts = []; d = 0; q = None; cur = []
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q: q = None
            continue
        if ch in "'\"": q = ch; cur.append(ch); continue
        if ch in '([{': d += 1
        elif ch in ')]}': d -= 1
        if ch == ',' and d == 0: parts.append(''.join(cur)); cur = []; continue
        cur.append(ch)
    if ''.join(cur).strip(): parts.append(''.join(cur))
    return [p.strip() for p in parts]

def rel_paths(arg):
    """top-level relationship paths in a with()/load() argument list"""
    out = []
    for p in split_top(arg):
        if p.startswith('['):
            inner = p[1:p.rfind(']')]
            for e in split_top(inner):
                m = re.match(r"""^['"]([^'"]+)['"]\s*(=>.*)?$""", e, re.S)
                if m: out.append((m.group(1), bool(m.group(2))))
                elif e: out.append(('?' + e[:40], False))
        else:
            m = re.match(r"""^['"]([^'"]+)['"]$""", p)
            if m: out.append((m.group(1), False))
            elif p: out.append(('?' + p[:40], False))
    clean = []
    for path, constrained in out:
        if path.startswith('?'): clean.append((path, constrained)); continue
        segs = [seg.split(':')[0].strip() for seg in path.split('.')]
        clean.append(('.'.join(segs), constrained))
    return clean

def functions(s):
    """(start_of_signature, body_open, body_close) for every function/closure"""
    res = []
    for m in re.finditer(r'\bfunction\b\s*&?\s*\w*\s*\(', s):
        po = m.end() - 1; pc = match_fwd(s, po)
        k = pc + 1
        mm = re.match(r'\s*use\s*\(', s[k:])
        if mm:
            uo = k + mm.end() - 1; k = match_fwd(s, uo) + 1
        mm = re.match(r'\s*(:\s*\??[\w\\|]+)?\s*\{', s[k:])
        if not mm: continue
        bo = k + mm.end() - 1; bc = match_fwd(s, bo)
        res.append((m.start(), bo, bc, s[po + 1:pc]))
    for m in re.finditer(r'\bfn\s*\(', s):
        po = m.end() - 1; pc = match_fwd(s, po)
        mm = re.match(r'\s*(:\s*\??[\w\\|]+)?\s*=>', s[pc + 1:])
        if not mm: continue
        start = pc + 1 + mm.end()
        # arrow fn body ends at depth-0 , ) ] or ;
        d = 0; q = None; end = len(s) - 1
        for j in range(start, len(s)):
            ch = s[j]
            if q:
                if ch == q: q = None
                continue
            if ch in "'\"": q = ch; continue
            if ch in '([{': d += 1
            elif ch in ')]}':
                if d == 0: end = j; break
                d -= 1
            elif ch in ',;' and d == 0: end = j; break
        res.append((m.start(), start, end, s[po + 1:pc]))
    return res

class Resolver:
    def __init__(self, system):
        self.system = system; self.rel = load_rel(system)
        self.models = {k[0] for k in self.rel} | {v[2].lower() for v in self.rel.values()}
        self.unresolved = []
    def related(self, model, name):
        if model is None: return None
        v = self.rel.get((model.lower(), name.lower()))
        return v[2] if v else None
    def canon(self, model):
        for k, v in self.rel.items():
            if v[0].lower() == model.lower(): return v[0]
            if v[2].lower() == model.lower(): return v[2]
        return model
    def chain_model(self, s, end, funcs, depth=0):
        """model of the expression ending just before position end (an '->' or '::' token start)"""
        steps = []; i = end
        if s.startswith('::', end):
            cm = re.search(r'([A-Za-z_\\]+)\s*$', s[:end])
            cls = cm.group(1).split('\\')[-1] if cm else None
            nm = re.match(r'::\s*(\w+)', s[end:])
            if cls in ('static', 'self', 'parent'): return None
            return self.class_model(cls, nm.group(1) if nm else '')
        while True:
            k = i - 1
            while k >= 0 and s[k].isspace(): k -= 1
            if k < 0: return None
            if s[k] == ')':
                o = match_back(s, k)
                pre = s[:o]; m = re.search(r'([A-Za-z_]\w*)\s*$', pre)
                if m:
                    name = m.group(1); before = pre[:m.start()].rstrip()
                    if before.endswith('->') or before.endswith('?->'):
                        steps.append(('call', name)); i = len(before) - (3 if before.endswith('?->') else 2); continue
                    if before.endswith('::'):
                        cm = re.search(r'([A-Za-z_\\]+)$', before[:-2].rstrip())
                        cls = cm.group(1).split('\\')[-1] if cm else None
                        return self.apply_steps(self.class_model(cls, name), steps)
                    # function call root
                    if name.lower() == 'auth' and steps and steps[-1] == ('call', 'user'):
                        return self.apply_steps('User', steps[:-1])
                    if name.lower() == 'auth': return None
                    if name.lower() in NONMODEL_FUNCS: return 'NONMODEL'
                    return None
                inner = s[o + 1:k]
                cm = re.search(r'clone\s+\$(\w+)', inner)
                if cm: return self.apply_steps(self.var_model(s, o, cm.group(1), funcs, depth), steps)
                return None
            m = re.search(r'\$(\w+)\s*$', s[:k + 1])
            if m:
                var = m.group(1)
                if var == 'request' and steps and steps[-1] == ('call', 'user'):
                    return self.apply_steps('User', steps[:-1])
                if var == 'this': return 'NONMODEL'
                return self.apply_steps(self.var_model(s, m.start(), var, funcs, depth), steps)
            m = re.search(r'([A-Za-z_]\w*)\s*$', s[:k + 1])
            if m:
                before = s[:m.start()].rstrip()
                if before.endswith('->') or before.endswith('?->'):
                    steps.append(('prop', m.group(1))); i = len(before) - (3 if before.endswith('?->') else 2); continue
                return None
            return None
    def class_model(self, cls, first_method):
        if cls is None: return None
        if cls in ('Auth',) and first_method == 'user': return 'User'
        if cls.lower() in self.models: return self.canon(cls)
        if cls in ('DB', 'Cache', 'Log', 'Mail', 'Storage', 'Route', 'Str', 'Carbon', 'Http', 'Excel', 'PDF', 'Pdf', 'DataTables', 'Hash', 'Validator', 'Session', 'Notification'): return 'NONMODEL'
        return None
    def apply_steps(self, model, steps):
        if model in (None, 'NONMODEL'): return model
        cur = model
        for kind, name in reversed(steps):
            if name in ('user',) and kind == 'call' and cur in ('Auth',): cur = 'User'; continue
            r = self.related(cur, name)
            if r: cur = r
        return cur
    def var_model(self, s, pos, var, funcs, depth):
        if depth > 6: return None
        if var in ('request',): return 'NONMODEL'
        encl = sorted([f for f in funcs if f[1] < pos <= f[2]], key=lambda f: f[2] - f[1])
        for (sig, bo, bc, params) in encl:
            body = s[bo:pos]
            assigns = [m for m in re.finditer(r'\$' + var + r'\s*=(?!=)\s*', body)]
            if assigns:
                a = assigns[-1]; st = bo + a.end()
                semi = st
                # find end of the assigned expression (depth-0 ';')
                d = 0; q = None
                for j in range(st, len(s)):
                    ch = s[j]
                    if q:
                        if ch == q: q = None
                        continue
                    if ch in "'\"": q = ch; continue
                    if ch in '([{': d += 1
                    elif ch in ')]}': d -= 1
                    elif ch == ';' and d == 0: semi = j; break
                expr = s[st:semi]
                if re.match(r'\s*(Auth::user\(\)|auth\(\)\s*->\s*user\(\)|\$request\s*->\s*user\(\)|Auth::guard\([^)]*\)\s*->\s*user\(\))', expr): return 'User'
                mm = re.match(r'\s*\(\s*clone\s+\$(\w+)\s*\)', expr) or re.match(r'\s*clone\s+\$(\w+)', expr)
                if mm: return self.var_model(s, st, mm.group(1), funcs, depth + 1)
                # resolve the expression: model of its chain up to the end
                return self.chain_model(s, semi, funcs, depth + 1) if expr.strip() else None
            fm = re.search(r'foreach\s*\(\s*(.+?)\s+as\s+(?:\$\w+\s*=>\s*)?\$' + var + r'\s*\)', body, re.S)
            if fm:
                src = fm.group(1).strip(); mm = re.match(r'\$(\w+)$', src)
                if mm: return self.var_model(s, bo + fm.start(), mm.group(1), funcs, depth + 1)
                end = bo + fm.start(1) + len(fm.group(1).rstrip())
                return self.chain_model(s, end, funcs, depth + 1)
            pm = re.search(r'([A-Z]\w*)\s+\$' + var + r'\b', params)
            if pm: return self.canon(pm.group(1)) if pm.group(1).lower() in self.models else ('NONMODEL' if pm.group(1) in ('Request',) else None)
            if re.search(r'\$' + var + r'\b', params):
                # closure parameter: constrained eager load or whereHas
                return ('CLOSURE', sig)
            um = re.search(r'\buse\s*\([^)]*\$' + var + r'\b', s[sig:bo])
            if um: continue  # look in the outer function
        return None

def scan(system):
    R = Resolver(system); calls = []
    files = []
    for sub in ('app', 'routes', 'resources/views'):
        root = os.path.join(BASES[system], sub)
        for dp, _, fs in os.walk(root):
            for f in fs:
                if f.endswith('.php'): files.append(os.path.join(dp, f))
    for p in sorted(files):
        raw = open(p, errors='ignore').read()
        blade = p.endswith('.blade.php')
        s = strip_blade(raw) if blade else strip_php(raw)
        funcs = functions(s)
        for m in re.finditer(r'(\?->|->|::)\s*(with|load|loadMissing)\s*\(', s):
            po = m.end() - 1; pc = match_fwd(s, po); arg = s[po + 1:pc]
            line = s.count('\n', 0, m.start()) + 1
            base = R.chain_model(s, m.start(), funcs)
            paths = rel_paths(arg)
            calls.append(dict(file=os.path.relpath(p, BASES[system]), line=line, kind=m.group(2), pos=m.start(),
                              base=base if not isinstance(base, tuple) else 'CLOSURE', closure_sig=base[1] if isinstance(base, tuple) else None,
                              paths=paths, raw=re.sub(r'\s+', ' ', arg)[:200]))
    return R, calls

def pairs_of(R, call):
    base = call['base']
    if base in (None, 'NONMODEL') or str(base).startswith('CLOSURE'): return set()
    out = set()
    for path, constrained in call['paths']:
        if path.startswith('?'): continue
        cur = base
        for seg in path.split('.'):
            key = (cur.lower(), seg.lower())
            if key in R.rel:
                src, meth, relm = R.rel[key]; out.add((src, meth)); cur = relm
            else:
                out.add((cur, seg + '?')); break
    return out


# Two call sites resolved by reading the code (the expression is not resolvable statically):
#  iTeams Api/KeberadaanApiController.php:470  $query = $baseQuery(); the closure builds Keberadaan::query() (line 404)
#  iTeams RoleController.php:277               Role::with('permissions'): Spatie Role model, not in the inventory
OVERRIDES = {('iTeams', 'app/Http/Controllers/Api/KeberadaanApiController.php', 470): 'Keberadaan',
             ('iTeams', 'app/Http/Controllers/RoleController.php', 277): 'EXTERNAL'}

def main():
    import argparse, collections
    ap = argparse.ArgumentParser()
    ap.add_argument('--system', required=True); ap.add_argument('--source', required=True)
    ap.add_argument('--inventory', required=True); ap.add_argument('--method-col', default='Method Name')
    ap.add_argument('--out-prefix', default='eager_load_')
    a = ap.parse_args()
    BASES[a.system] = a.source; INVENTORY[a.system] = (a.inventory, a.method_col)
    R, calls = scan(a.system)
    cnt = collections.Counter(); ctrl = collections.Counter(); sites = []
    for c in calls:
        base = OVERRIDES.get((a.system, c['file'], c['line']), c['base'])
        if base == 'EXTERNAL': continue
        c['base'] = base
        for p in pairs_of(R, c):
            if p[1].endswith('?'): continue
            cnt[p] += 1
            if c['file'].startswith('app/Http/Controllers'): ctrl[p] += 1
            sites.append([a.system, p[0] + '.' + p[1], c['file'], c['line'], c['kind'], base, c['raw']])
    with open(a.out_prefix + a.system + '_counts.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['system', 'relationship', 'eager_model_attributed', 'eager_model_attributed_controllers_only'])
        for (src_m, meth, rel_m) in R.rel.values():
            w.writerow([a.system, src_m + '.' + meth, cnt[(src_m, meth)], ctrl[(src_m, meth)]])
    with open(a.out_prefix + a.system + '_call_sites.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['system', 'relationship', 'file', 'line', 'method', 'base_model', 'arguments'])
        w.writerows(sorted(sites))

if __name__ == '__main__':
    main()
