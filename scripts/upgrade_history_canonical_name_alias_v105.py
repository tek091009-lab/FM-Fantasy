from __future__ import annotations
import base64,gzip,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=[ROOT/'app'/f'part{i:02d}' for i in range(17)]+[ROOT/'app'/f'fix{i}' for i in range(17,21)]

def reconstruct():
    return gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in PARTS))).decode()

def repack(html):
    packed=base64.b64encode(gzip.compress(html.encode(),compresslevel=9,mtime=0)).decode()
    step=(len(packed)+len(PARTS)-1)//len(PARTS)
    chunks=[packed[i*step:(i+1)*step] for i in range(len(PARTS))]
    assert ''.join(chunks)==packed
    for p,c in zip(PARTS,chunks):p.write_text(c+'\n')

html=reconstruct();m=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',html)
if not m:raise RuntimeError('FM_PY_SOURCE_B64 not found')
py=base64.b64decode(m.group(1)).decode()
if 'def confirmed_name_fixture_conditioned_global_pass():' not in py:
    raise RuntimeError('v104 retained-name stack must exist before v105')

# Keep the exact retained-name table authoritative. v105 adds a second, separately namespaced
# canonical representation only for rows whose exact text has NEVER been learned. This prevents
# a transfer/collision already visible in the exact table from being "rescued" by normalization.
store_old="    confirmed_retained_name_clubs=collections.defaultdict(set)\n"
store_new="    confirmed_retained_name_clubs=collections.defaultdict(set)\n    confirmed_retained_canonical_name_clubs=collections.defaultdict(set)\n"
if 'confirmed_retained_canonical_name_clubs=collections.defaultdict(set)' not in py:
    if store_old not in py:raise RuntimeError('v105 name-store anchor missing')
    py=py.replace(store_old,store_new,1)

helper_anchor="    def confirmed_name_club(rows,ids):\n"
helper_insert="""    def _retained_name_canonical_key(row):
        raw=str(row.get('player') or row.get('name') or '').strip()
        if not raw:return ''
        if raw.lower().startswith('player id '):return ''
        # FM retained strings can vary only in Unicode composition, accents or punctuation
        # across archive/schema paths. Canonicalization is deliberately lexical, never fuzzy:
        # no token re-ordering, initials expansion, edit distance, nickname guessing or surname
        # inference. Punctuation is removed rather than replaced so O'Neil == O’Neil == ONeil.
        import unicodedata as _ud
        s=_ud.normalize('NFKD',raw.casefold())
        s=''.join(ch for ch in s if not _ud.combining(ch))
        s=''.join(ch for ch in s if ch.isalnum() or ch.isspace())
        return ''.join(s.split())

    def _retained_name_owner_set(row):
        # Exact evidence always wins, including exact ambiguity. Canonical evidence is consulted
        # ONLY when this exact string has never been observed in an authoritative recovered match.
        key=_retained_name_key(row)
        if key and key in confirmed_retained_name_clubs:
            return confirmed_retained_name_clubs.get(key,set()),'exact'
        ckey=_retained_name_canonical_key(row)
        if ckey and ckey in confirmed_retained_canonical_name_clubs:
            return confirmed_retained_canonical_name_clubs.get(ckey,set()),'canonical'
        return set(),''

    def confirmed_name_club(rows,ids):
"""
if 'def _retained_name_owner_set(row):' not in py:
    if helper_anchor not in py:raise RuntimeError('v105 helper anchor missing')
    py=py.replace(helper_anchor,helper_insert,1)

# Teach canonical aliases only from the same authoritative registered matches that teach exact
# names. A canonical collision across clubs therefore becomes a multi-owner alias and is ignored.
learn_old="                _nkey=_retained_name_key(_row)\n                if _nkey:confirmed_retained_name_clubs[_nkey].add(_eid)\n"
learn_new="                _nkey=_retained_name_key(_row)\n                if _nkey:confirmed_retained_name_clubs[_nkey].add(_eid)\n                _ckey=_retained_name_canonical_key(_row)\n                if _ckey:confirmed_retained_canonical_name_clubs[_ckey].add(_eid)\n"
if 'confirmed_retained_canonical_name_clubs[_ckey].add(_eid)' not in py:
    if learn_old not in py:raise RuntimeError('v105 register-match learning anchor missing')
    py=py.replace(learn_old,learn_new,1)

# Every v99-v104 name-vote helper currently fetches owners directly from the exact table. Route
# those lookups through the exact-first/canonical-second resolver without changing any threshold.
old_lookup="owners=confirmed_retained_name_clubs.get(key,set())"
new_lookup="owners,_name_source=_retained_name_owner_set(row)\n            if _name_source=='canonical':diagnostics['confirmed_name_canonical_alias_uses']+=1"
lookup_count=py.count(old_lookup)
if lookup_count:
    py=py.replace(old_lookup,new_lookup)
if old_lookup in py:raise RuntimeError('v105 direct exact-only owner lookup remains')
if lookup_count<3:
    raise RuntimeError(f'v105 expected multiple retained-name owner lookups, found {lookup_count}')

diag_anchor="    diagnostics.setdefault('confirmed_name_ambiguous_aliases',0)\n"
diag_new=diag_anchor+"    diagnostics.setdefault('confirmed_name_canonical_alias_uses',0)\n    diagnostics.setdefault('confirmed_name_canonical_ambiguous_aliases',0)\n"
if "diagnostics.setdefault('confirmed_name_canonical_alias_uses',0)" not in py:
    if diag_anchor not in py:raise RuntimeError('v105 diagnostic anchor missing')
    py=py.replace(diag_anchor,diag_new,1)

# Canonical ambiguity is tracked separately when a fallback lexical form maps to multiple clubs.
amb_old="            if len(owners)!=1:\n                if len(owners)>1:diagnostics['confirmed_name_ambiguous_aliases']+=1\n                continue\n"
amb_new="            if len(owners)!=1:\n                if len(owners)>1:\n                    if _name_source=='canonical':diagnostics['confirmed_name_canonical_ambiguous_aliases']+=1\n                    else:diagnostics['confirmed_name_ambiguous_aliases']+=1\n                continue\n"
if amb_old in py:
    py=py.replace(amb_old,amb_new)

handoff_anchor="'unlabelled_rich_confirmed_name_ambiguous_aliases':member_rich_diag.get('confirmed_name_ambiguous_aliases',0),"
handoff_new=handoff_anchor+"'unlabelled_rich_confirmed_name_canonical_alias_uses':member_rich_diag.get('confirmed_name_canonical_alias_uses',0),'unlabelled_rich_confirmed_name_canonical_ambiguous_aliases':member_rich_diag.get('confirmed_name_canonical_ambiguous_aliases',0),"
if 'unlabelled_rich_confirmed_name_canonical_alias_uses' not in py:
    if handoff_anchor not in py:raise RuntimeError('v105 handoff anchor missing')
    py=py.replace(handoff_anchor,handoff_new,1)

compile(py,'fm_importer.py','exec')
new_b64=base64.b64encode(py.encode()).decode();html=html[:m.start(1)]+new_b64+html[m.end(1):];repack(html)
chk=reconstruct();mm=re.search(r'const FM_PY_SOURCE_B64\s*=\s*"([^"]+)"',chk);assert mm
cpy=base64.b64decode(mm.group(1)).decode();compile(cpy,'fm_importer.py','exec')
for s in [
    'confirmed_retained_canonical_name_clubs=collections.defaultdict(set)',
    'def _retained_name_canonical_key(row):',
    "_ud.normalize('NFKD',raw.casefold())",
    'def _retained_name_owner_set(row):',
    "return confirmed_retained_name_clubs.get(key,set()),'exact'",
    "return confirmed_retained_canonical_name_clubs.get(ckey,set()),'canonical'",
    'confirmed_retained_canonical_name_clubs[_ckey].add(_eid)',
    "confirmed_name_canonical_alias_uses",
    'unlabelled_rich_confirmed_name_canonical_alias_uses',
    'def confirmed_name_fixture_conditioned_global_pass():',
    'def confirmed_name_fixture_conditioned_pair_pass():',
    'def confirmed_name_global_constraint_pass():',
]:assert s in cpy,s
assert 'owners=confirmed_retained_name_clubs.get(key,set())' not in cpy
print(f'v105 canonical retained-name alias fallback applied across {lookup_count} owner lookups')