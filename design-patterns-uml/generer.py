"""Génère les fichiers PlantUML (.puml) et XMI 2.1 (.xmi) à partir des blocs
Mermaid de ../design-patterns-cheatsheet.md.

Usage : python3 generer.py   (depuis n'importe quel dossier)
"""
import re, os, textwrap, unicodedata
from xml.sax.saxutils import escape, quoteattr

OUT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(OUT, '..', 'design-patterns-cheatsheet.md')

md = open(SRC, encoding='utf8').read()

# ---------------------------------------------------------------- parsing md
FAMILIES = {'2': 'Création', '3': 'Structure', '4': 'Comportement', '5': 'Architecture',
            '6': 'Révision'}
patterns, fam = [], None
for sec in re.split(r'\n(?=## |### )', md):
    m = re.match(r'## (\d)\.', sec)
    if m:
        fam = FAMILIES.get(m.group(1)); continue
    m = re.match(r'### (.+)', sec)
    if not m or fam is None:
        continue
    title = re.sub(r'\s*\(.*\)', '', m.group(1)).replace('⭐', '').strip()
    blocks = re.findall(r'```mermaid\n(.*?)```', sec, re.S)
    cls = [b for b in blocks if b.startswith('classDiagram')]
    if not cls:
        continue
    but = re.search(r'\*\*But :\*\* (.+)', sec).group(1)
    lec = re.search(r'🔎 \*\*Lecture :\*\* (.+)', sec)
    patterns.append(dict(
        title=title, family=fam, but=but, lecture=lec.group(1) if lec else '',
        cls=cls[0],
        state=next((b for b in blocks if b.startswith('stateDiagram')), None),
        seq=next((b for b in blocks if b.startswith('sequenceDiagram')), None)))

def gen(t):  # List~X~ -> List<X>
    return re.sub(r'~([^~]*)~', r'<\1>', t)

OP = re.compile(r'^([+\-#~])?(\w+)\((.*?)\)\s*(.*?)\s*([$*])?$')
AT = re.compile(r'^([+\-#~])?(\w+)\s*:\s*(.+?)\s*([$*])?$')
REL = re.compile(r'^(\w+)\s*(?:"([^"]+)"\s*)?(<\|--|<\|\.\.|o--|\*--|-->|\.\.>)\s*'
                 r'(?:"([^"]+)"\s*)?(\w+)\s*(?::\s*(.+))?$')

MULT_RE = re.compile(r'^(\d+|\*|\d+\.\.(\d+|\*))$')

def end_label(s):
    """Texte en bout de flèche : "-role *" -> (vis, role, mult)."""
    vis = role = mult = None
    for tok in (s or '').split():
        if MULT_RE.match(tok):
            mult = tok
        elif (m := re.match(r'^([+\-#~])?(\w+)$', tok)):
            vis, role = m.group(1) or '+', m.group(2)
    return vis, role, mult

def parse_class_diagram(src):
    classes, rels, notes, order = {}, [], [], []
    def get(name):
        base = name.split('~')[0]
        if base not in classes:
            classes[base] = dict(name=base, display=gen(name), kind='class',
                                 attrs=[], ops=[], ns=None)
            order.append(base)
        return classes[base]
    cur, ns = None, None
    for raw in src.splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        if cur is None and (m := re.match(r'namespace (\w+)\s*\{$', line)):
            ns = m.group(1); continue
        if cur is None and line == '}' and ns:
            ns = None; continue
        if cur is not None:
            if line == '}':
                cur = None
            elif line == '<<interface>>':
                cur['kind'] = 'interface'
            elif line == '<<abstract>>':
                cur['kind'] = 'abstract'
            elif (m := OP.match(line)):
                vis, name, params, ret, mod = m.groups()
                ps = []
                for p in filter(None, (x.strip() for x in params.split(','))):
                    n, _, t = p.partition(':')
                    ps.append((n.strip(), gen(t.strip())))
                cur['ops'].append(dict(vis=vis or '+', name=name, params=ps,
                                       ret=gen(ret) if ret else None,
                                       static=mod == '$', abstract=mod == '*'))
            elif (m := AT.match(line)):
                vis, name, typ, mod = m.groups()
                typ, _, default = typ.partition(' = ')
                cur['attrs'].append(dict(vis=vis or '+', name=name, type=gen(typ.strip()),
                                         default=default.strip() or None, static=mod == '$'))
            else:
                raise ValueError(f'membre non reconnu: {line}')
            continue
        if (m := re.match(r'class (\S+?)\s*(\{)?$', line)):
            c = get(m.group(1))
            c['display'] = gen(m.group(1))
            c['ns'] = ns
            if m.group(2):
                cur = c
        elif (m := re.match(r'note for (\w+) "(.*)"$', line)):
            notes.append((m.group(1), m.group(2).replace('\\n', '\n')))
        elif (m := REL.match(line)):
            a, ma, op, mb, b, label = m.groups()
            get(a); get(b)
            rels.append(dict(a=a, b=b, op=op, ma=ma, mb=mb, label=label))
        else:
            raise ValueError(f'ligne non reconnue: {line}')
    return [classes[n] for n in order], rels, notes

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# ------------------------------------------------------------ PlantUML output
def creole(s):
    s = s.replace('`~`', '""∼""')  # ~ est un caractère spécial en PlantUML : on affiche ∼ (U+223C)
    s = re.sub(r'`([^`]+)`', r'""\1""', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'//\1//', s)
    return s

NBSP = ' '
def wrap(s, width=95):
    """Coupe les lignes sans casser le gras, l'italique ou le code."""
    s = re.sub(r'(\*\*.+?\*\*|"".+?""|//.+?//)', lambda m: m.group(0).replace(' ', NBSP), s)
    return [l.replace(NBSP, ' ') for l in textwrap.wrap(s, width)]

# Indications de placement propres à PlantUML (le modèle UML reste identique).
PUML_LAYOUT = {
    'Abstract Factory': {
        ('Bouton', '<|..', 'MacBouton'): 'MacBouton .down.|> Bouton',
        ('Bouton', '<|..', 'WinBouton'): 'WinBouton .down.|> Bouton',
        ('Menu', '<|..', 'MacMenu'): 'MacMenu .down.|> Menu',
        ('Menu', '<|..', 'WinMenu'): 'WinMenu .down.|> Menu',
        'extra': ['MacMenu -[hidden]right- WinBouton'],
    },
    'Bridge': {
        ('Telecommande', 'o--', 'Appareil'): 'Telecommande o-right- Appareil : le pont',
    },
    'ON/OFF : MVC + Observer + Command': {
        ('LabelView', '-->', 'Label'): 'LabelView -right-> "-label" Label',
    },
}

def puml_member(m, is_op):
    mods = ('{static} ' if m.get('static') else '') + ('{abstract} ' if m.get('abstract') else '')
    if is_op:
        params = ', '.join(f'{n} : {t}' for n, t in m['params'])
        ret = f' : {m["ret"]}' if m['ret'] else ''
        return f'  {mods}{m["vis"]}{m["name"]}({params}){ret}'
    default = f' = {m["default"]}' if m.get('default') else ''
    return f'  {mods}{m["vis"]}{m["name"]} : {m["type"]}{default}'

# Namespaces Mermaid : nom affiché (packages XMI) et couleur (PlantUML).
# En PlantUML on colore au lieu de dessiner des packages : la mise en page reste lisible.
NS_LABELS = {'Modele': 'Modèle', 'Vue': 'Vue', 'Controleur': 'Contrôleur',
             'AWT': 'Composants AWT (fournis par Java)', 'Noyau': 'Noyau fonctionnel',
             'Commande': 'Commandes (pattern Command)'}
NS_COLORS = {'Modele': ('#DDEBFF', 'bleu'), 'Vue': ('#DFF5E1', 'vert'),
             'Controleur': ('#FFE4CC', 'orange'), 'AWT': ('#EEEEEE', 'gris'),
             'Noyau': ('#FFF6BF', 'jaune'), 'Commande': ('#EDE3FF', 'violet')}

def merge_parallel(rels):
    """Fusionne les associations parallèles sans libellé (A *-- "r1" B, A *-- "r2" B)
    en un seul trait avec un rôle par ligne. Le XMI garde des associations distinctes."""
    out, seen = [], {}
    for r in rels:
        key = (r['a'], r['op'], r['b'], r['ma'])
        if r['op'] in ('o--', '*--', '-->') and not r['label'] and r['mb'] and key in seen:
            seen[key]['mb'] += '\\n' + r['mb']
            continue
        r = dict(r)
        seen.setdefault(key, r)
        out.append(r)
    return out

def puml_header(name, title):
    return [f'@startuml {name}', '!pragma layout smetana', f'title {title}',
            'skinparam classAttributeIconSize 0', 'skinparam shadowing false',
            'skinparam defaultFontName Arial', 'hide circle', 'hide empty members', '']

def to_puml(p, n, classes, rels, notes):
    out = puml_header(f'{n:02d}-{slug(p["title"])}', f'{p["title"]} — {p["family"]}')
    for c in classes:
        kw = {'interface': 'interface', 'abstract': 'abstract class', 'class': 'class'}[c['kind']]
        st = {'interface': ' <<interface>>', 'abstract': ' <<abstract>>', 'class': ''}[c['kind']]
        color = f' {NS_COLORS[c["ns"]][0]}' if c['ns'] in NS_COLORS else ''
        body = [puml_member(a, False) for a in c['attrs']] + [puml_member(o, True) for o in c['ops']]
        out.append(f'{kw} {c["display"]}{st}{color}' + (' {' if body else ''))
        if body:
            out += body + ['}']
    out.append('')
    layout = PUML_LAYOUT.get(p['title'], {})
    for r in merge_parallel(rels):
        if (r['a'], r['op'], r['b']) in layout:
            out.append(layout[(r['a'], r['op'], r['b'])]); continue
        ma = f' "{r["ma"]}"' if r['ma'] else ''
        mb = f'"{r["mb"]}" ' if r['mb'] else ''
        lab = f' : {r["label"]}' if r['label'] else ''
        out.append(f'{r["a"]}{ma} {r["op"]} {mb}{r["b"]}{lab}')
    out += layout.get('extra', [])
    for target, text in notes:
        out += ['', f'note bottom of {target}', *text.split('\n'), 'end note']
    out += ['', 'legend bottom left', *wrap(f'**But :** {creole(p["but"])}')]
    used = [ns for ns in dict.fromkeys(c['ns'] for c in classes) if ns in NS_COLORS]
    if used:
        out += [' ', '**Couleurs :** ' + ', '.join(
            f'<back:{NS_COLORS[ns][0]}> {NS_COLORS[ns][1]} </back> = {NS_LABELS[ns]}' for ns in used)]
    if p['lecture']:
        out += [' '] + wrap(f'**Lecture :** {creole(p["lecture"])}')
    out += ['endlegend', '@enduml', '']
    return '\n'.join(out)

def state_puml(p, n):
    out = puml_header(f'{n:02d}-{slug(p["title"])}-transitions',
                      f'{p["title"]} — transitions entre états')[:3] + ['']
    out += [l.strip() for l in p['state'].splitlines()[1:] if l.strip()]
    return '\n'.join(out + ['@enduml', ''])

def seq_puml(p, n):
    out = puml_header(f'{n:02d}-{slug(p["title"])}-sequence',
                      f'{p["title"]} — déroulement')[:3]
    out += ['skinparam defaultFontName Arial', 'skinparam shadowing false', 'autonumber', '']
    for l in (l.strip() for l in p['seq'].splitlines()[1:]):
        if (m := re.match(r'(actor|participant) (\w+) as (.+)$', l)):
            out.append(f'{m.group(1)} "{m.group(3)}" as {m.group(2)}')
        elif (m := re.match(r'(\w+)(-->>|->>)(\w+): (.+)$', l)):
            arrow = '-->' if m.group(2) == '-->>' else '->'
            out.append(f'{m.group(1)} {arrow} {m.group(3)} : {m.group(4)}')
        elif (m := re.match(r'Note (over|left of|right of) ([\w,]+): (.+)$', l)):
            out.append(f'note {m.group(1)} {m.group(2).replace(",", ", ")} : {m.group(3)}')
        elif l:
            raise ValueError(f'séquence non reconnue: {l}')
    return '\n'.join(out + ['@enduml', ''])

# ----------------------------------------------------------------- XMI output
VIS = {'+': 'public', '-': 'private', '#': 'protected', '~': 'package'}
MULT = {'1': ('1', '1'), '*': ('0', '*'), '0..1': ('0', '1'), '1..*': ('1', '*')}
COLL = re.compile(r'^(?:List|Deque|Set|Collection)<(\w+)>$')

class Ids:
    def __init__(self, prefix): self.p, self.n = prefix, 0
    def __call__(self, kind='e'):
        self.n += 1
        return f'{self.p}_{kind}{self.n}'

def mult_xml(ids, m, ind):
    if not m:
        return ''
    lo, hi = MULT.get(m, (m, m))
    return (f'{ind}<lowerValue xmi:type="uml:LiteralInteger" xmi:id="{ids("lv")}" value="{lo}"/>\n'
            f'{ind}<upperValue xmi:type="uml:LiteralUnlimitedNatural" xmi:id="{ids("uv")}" value="{hi}"/>\n')

def to_xmi_package(p, n, classes, rels, notes, ind='    '):
    ids = Ids(f'p{n:02d}')
    cid = {c['name']: ids('c') for c in classes}
    types = {}  # types externes (String, int, List<Element>…) -> DataType

    def tref(t):
        if t is None:
            return None
        base = t.split('<')[0]
        if base in cid:
            return cid[base]
        if t not in types:
            types[t] = ids('t')
        return types[t]

    # Un attribut déjà présent qui correspond à une association devient
    # l'extrémité navigable de cette association (au lieu d'un doublon).
    extra_attrs = {c['name']: [] for c in classes}
    assoc_xml, dep_xml, gen_of, real_of = [], [], {}, {}
    for r in rels:
        a, b, op = r['a'], r['b'], r['op']
        if op == '<|--':
            gen_of.setdefault(b, []).append(a)
        elif op == '<|..':
            real_of.setdefault(b, []).append(a)
        elif op == '..>':
            d = ids('d')
            name = f' name={quoteattr(r["label"])}' if r['label'] else ''
            dep_xml.append(f'{ind}  <packagedElement xmi:type="uml:Dependency" xmi:id="{d}"{name} '
                           f'client="{cid[a]}" supplier="{cid[b]}"/>\n')
        else:
            agg = {'o--': 'shared', '*--': 'composite', '-->': 'none'}[op]
            asid, e_other = ids('as'), ids('p')
            src = next(c for c in classes if c['name'] == a)
            vis_b, role_b, mult_b = end_label(r['mb'])
            mult_a = end_label(r['ma'])[2]
            free = [at for at in src['attrs'] if not at.get('_used') and
                    (at['type'] == b or (COLL.match(at['type']) and
                                         COLL.match(at['type']).group(1) == b))]
            existing = (next((at for at in free if at['name'] == (role_b or r['label'])), None)
                        or (None if role_b else next(iter(free), None)))
            if existing:
                existing['_used'] = True
                existing['_assoc'], existing['_agg'] = asid, agg
                existing['_mult'] = mult_b or ('*' if COLL.match(existing['type']) else None)
                existing['_type'] = b
                e_nav = existing.setdefault('_id', ids('p'))
            else:
                e_nav = ids('p')
                role = role_b or (r['label'] if r['label'] and re.fullmatch(r'\w+', r['label'])
                                  else b[0].lower() + b[1:])
                extra_attrs[a].append(dict(vis=vis_b or '-', name=role, type=b, _id=e_nav,
                                           _assoc=asid, _agg=agg, _mult=mult_b, _type=b))
            name = f' name={quoteattr(r["label"])}' if r['label'] else ''
            assoc_xml.append(
                f'{ind}  <packagedElement xmi:type="uml:Association" xmi:id="{asid}"{name} '
                f'memberEnd="{e_nav} {e_other}">\n'
                f'{ind}    <ownedEnd xmi:type="uml:Property" xmi:id="{e_other}" '
                f'type="{cid[a]}" association="{asid}">\n'
                + mult_xml(ids, mult_a, ind + '      ') +
                f'{ind}    </ownedEnd>\n{ind}  </packagedElement>\n')

    pkg_name = f"{n:02d} - {p['title']}"
    x = [f'{ind}<packagedElement xmi:type="uml:Package" xmi:id="{ids("pk")}" '
         f'name={quoteattr(pkg_name)}>\n']
    x.append(f'{ind}  <ownedComment xmi:type="uml:Comment" xmi:id="{ids("cm")}">'
             f'<body>{escape("But : " + re.sub(r"[*`]", "", p["but"]))}</body></ownedComment>\n')
    chunks = {}  # XML de chaque classe, rangé ensuite dans son sous-package éventuel
    for c in classes:
        start = len(x)
        xt = 'uml:Interface' if c['kind'] == 'interface' else 'uml:Class'
        abstract = ' isAbstract="true"' if c['kind'] != 'class' else ''
        x.append(f'{ind}  <packagedElement xmi:type="{xt}" xmi:id="{cid[c["name"]]}" '
                 f'name={quoteattr(c["display"])}{abstract}>\n')
        for g in gen_of.get(c['name'], []):
            x.append(f'{ind}    <generalization xmi:type="uml:Generalization" '
                     f'xmi:id="{ids("g")}" general="{cid[g]}"/>\n')
        for i in real_of.get(c['name'], []):
            x.append(f'{ind}    <interfaceRealization xmi:type="uml:InterfaceRealization" '
                     f'xmi:id="{ids("r")}" client="{cid[c["name"]]}" supplier="{cid[i]}" '
                     f'contract="{cid[i]}"/>\n')
        for at in c['attrs'] + extra_attrs[c['name']]:
            pid = at.setdefault('_id', ids('p'))
            extra = ''
            if '_assoc' in at:
                extra = f' association="{at["_assoc"]}" aggregation="{at["_agg"]}"'
            static = ' isStatic="true"' if at.get('static') else ''
            typ = tref(at.get('_type', at['type']))
            mx = mult_xml(ids, at.get('_mult'), ind + '      ')
            if at.get('default'):
                lit = 'uml:LiteralInteger' if at['default'].isdigit() else 'uml:LiteralString'
                mx += (f'{ind}      <defaultValue xmi:type="{lit}" xmi:id="{ids("dv")}" '
                       f'value={quoteattr(at["default"])}/>\n')
            head = (f'{ind}    <ownedAttribute xmi:type="uml:Property" xmi:id="{pid}" '
                    f'name={quoteattr(at["name"])} visibility="{VIS[at["vis"]]}" type="{typ}"'
                    f'{static}{extra}')
            x.append(head + (f'>\n{mx}{ind}    </ownedAttribute>\n' if mx else '/>\n'))
        for o in c['ops']:
            mods = (' isStatic="true"' if o['static'] else '') + (' isAbstract="true"' if o['abstract'] else '')
            x.append(f'{ind}    <ownedOperation xmi:type="uml:Operation" xmi:id="{ids("o")}" '
                     f'name={quoteattr(o["name"])} visibility="{VIS[o["vis"]]}"{mods}>\n')
            for pn, pt in o['params']:
                x.append(f'{ind}      <ownedParameter xmi:type="uml:Parameter" xmi:id="{ids("pa")}" '
                         f'name={quoteattr(pn)} direction="in" type="{tref(pt)}"/>\n')
            if o['ret']:
                x.append(f'{ind}      <ownedParameter xmi:type="uml:Parameter" xmi:id="{ids("pa")}" '
                         f'direction="return" type="{tref(o["ret"])}"/>\n')
            x.append(f'{ind}    </ownedOperation>\n')
        x.append(f'{ind}  </packagedElement>\n')
        chunks[c['name']] = x[start:]
        del x[start:]
    for ns in dict.fromkeys(c['ns'] for c in classes):
        body = [l for c in classes if c['ns'] == ns for l in chunks[c['name']]]
        if ns is None:
            x += body
        else:
            x.append(f'{ind}  <packagedElement xmi:type="uml:Package" xmi:id="{ids("pk")}" '
                     f'name={quoteattr(NS_LABELS.get(ns, ns))}>\n')
            x += ['  ' + l for l in ''.join(body).splitlines(keepends=True)]
            x.append(f'{ind}  </packagedElement>\n')
    x += assoc_xml + dep_xml
    for target, text in notes:
        x.append(f'{ind}  <ownedComment xmi:type="uml:Comment" xmi:id="{ids("cm")}" '
                 f'annotatedElement="{cid[target]}"><body>{escape(text)}</body></ownedComment>\n')
    for t, tid in types.items():
        x.append(f'{ind}  <packagedElement xmi:type="uml:DataType" xmi:id="{tid}" name={quoteattr(t)}/>\n')
    x.append(f'{ind}</packagedElement>\n')
    return ''.join(x)

def xmi_doc(name, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<xmi:XMI xmi:version="2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1" '
            'xmlns:uml="http://schema.omg.org/spec/UML/2.1">\n'
            f'  <uml:Model xmi:type="uml:Model" xmi:id="model" name={quoteattr(name)}>\n'
            f'{body}  </uml:Model>\n</xmi:XMI>\n')

# ------------------------------------------------------------------- écriture
os.makedirs(f'{OUT}/plantuml', exist_ok=True)
os.makedirs(f'{OUT}/xmi', exist_ok=True)
all_pk = []
for n, p in enumerate(patterns, 1):
    s = f'{n:02d}-{slug(p["title"])}'
    classes, rels, notes = parse_class_diagram(p['cls'])
    open(f'{OUT}/plantuml/{s}.puml', 'w', encoding='utf8').write(to_puml(p, n, classes, rels, notes))
    if p['state']:
        open(f'{OUT}/plantuml/{s}-transitions.puml', 'w', encoding='utf8').write(state_puml(p, n))
    if p['seq']:
        open(f'{OUT}/plantuml/{s}-sequence.puml', 'w', encoding='utf8').write(seq_puml(p, n))
    pk = to_xmi_package(p, n, classes, rels, notes)
    all_pk.append(pk)
    open(f'{OUT}/xmi/{s}.xmi', 'w', encoding='utf8').write(xmi_doc(p['title'], pk))
open(f'{OUT}/xmi/00-tous-les-patterns.xmi', 'w', encoding='utf8').write(
    xmi_doc('Design Patterns (GoF + MVC)', ''.join(all_pk)))
print(len(patterns), 'patterns :', ', '.join(p['title'] for p in patterns))
