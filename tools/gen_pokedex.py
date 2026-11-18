#!/usr/bin/env python3
"""Build the Traditional Chinese Pokédex data files for the 小智 device tool.

Input: PokeAPI CSV dump (github.com/PokeAPI/pokeapi data/v2/csv).
Output (in <out>):
  index.txt          one "key<TAB>kind/id" per line; kinds p=寶可夢 m=招式 a=特性 t=屬性
  p/<id>.json        one Pokémon species
  m/<id>.json        one move
  a/<id>.json        one ability
  t/<id>.json        one type
Every text field is the official zh-Hant (Taiwan/Hong Kong) text from PokeAPI.
"""
import csv
import collections
import json
import os
import re
import sys
import unicodedata

CSV, OUT = sys.argv[1], sys.argv[2]
ZH, HANS, EN = '4', '12', '9'
NUM_SPECIES = 1025
NUM_TYPES = 18


def rows(name):
    with open(os.path.join(CSV, name + '.csv'), encoding='utf-8') as f:
        yield from csv.DictReader(f)


def names(table, id_col, lang, col='name'):
    out = {}
    for r in rows(table):
        if r['local_language_id'] == lang and r[col]:
            out[int(r[id_col])] = r[col].strip()
    return out


def clean(text):
    text = text.replace('­\n', '').replace('­', '').replace('\f', '')
    text = re.sub(r'\s*\n\s*', '', text)  # Chinese text: line breaks carry no spaces
    text = re.sub(r'(?<=[^\x00-\x7f])[ \u3000]+|[ \u3000]+(?=[^\x00-\x7f])', '', text)
    return text.strip()


# ---------- names ----------
sp_zh = names('pokemon_species_names', 'pokemon_species_id', ZH)
sp_hans = names('pokemon_species_names', 'pokemon_species_id', HANS)
sp_en = names('pokemon_species_names', 'pokemon_species_id', EN)
genus_zh = names('pokemon_species_names', 'pokemon_species_id', ZH, 'genus')
type_zh = names('type_names', 'type_id', ZH)
type_hans = names('type_names', 'type_id', HANS)
type_en = names('type_names', 'type_id', EN)
ab_zh = names('ability_names', 'ability_id', ZH)
ab_hans = names('ability_names', 'ability_id', HANS)
ab_en = names('ability_names', 'ability_id', EN)
mv_zh = names('move_names', 'move_id', ZH)
mv_hans = names('move_names', 'move_id', HANS)
mv_en = names('move_names', 'move_id', EN)
item_zh = names('item_names', 'item_id', ZH)
item_en = names('item_names', 'item_id', EN)

species = {int(r['id']): r for r in rows('pokemon_species') if int(r['id']) <= NUM_SPECIES}
default_pokemon = {}  # species id -> pokemon row (default form)
for r in rows('pokemon'):
    if r['is_default'] == '1' and int(r['species_id']) in species:
        default_pokemon[int(r['species_id'])] = r

ptypes = collections.defaultdict(list)
for r in rows('pokemon_types'):
    ptypes[int(r['pokemon_id'])].append((int(r['slot']), int(r['type_id'])))

stat_zh = {1: 'HP', 2: '攻擊', 3: '防禦', 4: '特攻', 5: '特防', 6: '速度'}
pstats = collections.defaultdict(dict)
for r in rows('pokemon_stats'):
    sid = int(r['stat_id'])
    if sid in stat_zh:
        pstats[int(r['pokemon_id'])][stat_zh[sid]] = int(r['base_stat'])

pabilities = collections.defaultdict(list)
ability_owners = collections.defaultdict(list)
for r in rows('pokemon_abilities'):
    pid, aid = int(r['pokemon_id']), int(r['ability_id'])
    pabilities[pid].append((int(r['slot']), aid, r['is_hidden'] == '1'))
    if pid <= NUM_SPECIES:
        ability_owners[aid].append(pid)

# ---------- type chart ----------
eff = {}  # (attack, defend) -> factor (1.0 when absent)
for r in rows('type_efficacy'):
    a, d = int(r['damage_type_id']), int(r['target_type_id'])
    if a <= NUM_TYPES and d <= NUM_TYPES:
        eff[(a, d)] = int(r['damage_factor']) / 100


def defence(types):
    result = {}
    for atk in range(1, NUM_TYPES + 1):
        f = 1.0
        for d in types:
            f *= eff.get((atk, d), 1.0)
        result[atk] = f
    return result


def tn(ids):
    return [type_zh[i] for i in ids]


# ---------- flavor text (latest zh-Hant entry) ----------
def latest_flavor(table, id_col, version_col, order_of):
    best = {}
    for r in rows(table):
        if r['language_id'] != ZH:
            continue
        key = int(r[id_col])
        rank = order_of(int(r[version_col]))
        text = clean(r['flavor_text'])
        if text and (key not in best or rank >= best[key][0]):
            best[key] = (rank, text)
    return {k: v[1] for k, v in best.items()}


version_order = {int(r['id']): int(r['id']) for r in rows('versions')}
vg_order = {int(r['id']): int(r['order']) for r in rows('version_groups')}
sp_flavor = latest_flavor('pokemon_species_flavor_text', 'species_id', 'version_id',
                          lambda v: version_order.get(v, 0))
mv_flavor = latest_flavor('move_flavor_text', 'move_id', 'version_group_id',
                          lambda v: vg_order.get(v, 0))
ab_flavor = latest_flavor('ability_flavor_text', 'ability_id', 'version_group_id',
                          lambda v: vg_order.get(v, 0))

# ---------- moves ----------
moves = {int(r['id']): r for r in rows('moves')}
dmg_class = {'1': '變化', '2': '物理', '3': '特殊'}

# Level-up moves from the newest game the Pokémon appears in.
levelup = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows('pokemon_moves'):
    pid = int(r['pokemon_id'])
    if pid > NUM_SPECIES or r['pokemon_move_method_id'] != '1':
        continue
    levelup[pid][int(r['version_group_id'])].append((int(r['level'] or 0), int(r['move_id'])))


def pick_levelup(pid):
    groups = levelup.get(pid)
    if not groups:
        return []
    preferred = [25, 20, 18, 17, 16, 15]  # 朱紫, 劍盾, 究極日月, 日月, ORAS, XY
    vg = next((g for g in preferred if len(groups.get(g, [])) > 1), None)
    if vg is None:
        vg = max(groups, key=lambda g: (len(groups[g]) > 3, vg_order.get(g, 0)))
    seen, out = set(), []
    for level, mid in sorted(groups[vg]):
        if mid in seen or mid not in mv_zh:
            continue
        seen.add(mid)
        out.append(f"{'進化時' if level == 0 else f'Lv{level}'} {mv_zh[mid]}")
    return out[:30]


# ---------- evolution ----------
time_zh = {'day': '白天', 'night': '晚上', 'dusk': '黃昏'}


def evo_condition(r):
    t = r['evolution_trigger_id']
    reqs = []
    if r['minimum_happiness']:
        reqs.append('親密度高')
    if r['minimum_affection']:
        reqs.append('友好度高')
    if r['minimum_beauty']:
        reqs.append('美麗度高')
    if r['known_move_id']:
        reqs.append(f"學會{mv_zh.get(int(r['known_move_id']), '特定招式')}")
    if r['known_move_type_id']:
        reqs.append(f"學會{type_zh[int(r['known_move_type_id'])]}屬性招式")
    if r['held_item_id']:
        reqs.append(f"攜帶{item_zh.get(int(r['held_item_id']), '道具')}")
    if r['location_id']:
        reqs.append('在特定地點')
    if r['time_of_day'] in time_zh:
        reqs.append(time_zh[r['time_of_day']])
    if r['gender_id'] == '1':
        reqs.append('母的')
    elif r['gender_id'] == '2':
        reqs.append('公的')
    if t == '1':
        level = f"等級{r['minimum_level']}" if r['minimum_level'] else ''
        if not reqs:
            return level or '升級'
        return (level + '、' if level else '') + '、'.join(reqs) + '時升級'
    if t == '2':
        if r['trade_species_id']:
            reqs.append(f"和{sp_zh.get(int(r['trade_species_id']), '特定寶可夢')}交換")
        return '通訊交換' + (f"（{'、'.join(reqs)}）" if reqs else '')
    if t == '3':
        text = f"使用{item_zh.get(int(r['trigger_item_id'] or 0), '道具')}"
        return text + (f"（{'、'.join(reqs)}）" if reqs else '')
    special = {'4': '升級時隊伍有空位且背包有精靈球', '5': '攜帶糖飾品轉圈圈',
               '8': '在一場戰鬥中擊中要害3次', '9': '受到很多傷害後走到特定地點',
               '14': '使用特定招式很多次後升級', '15': '打倒3隻劈斬司令後升級',
               '16': '收集999枚索財靈的硬幣後升級', '17': '在寶可夢GO收集400顆美錄坦糖果',
               '13': '受到反作用力傷害累積很多後升級', '6': '在惡之塔修行', '7': '在水之塔修行',
               '11': '用迅疾攻擊使用特定招式很多次', '12': '用剛猛攻擊使用特定招式很多次'}
    fallback = f"等級{r['minimum_level']}" if r['minimum_level'] else '特殊條件'
    return special.get(t, fallback)


evo_cond = {}
for r in rows('pokemon_evolution'):
    sid = int(r['evolved_species_id'])
    if sid in species and sid not in evo_cond:
        evo_cond[sid] = evo_condition(r)

chains = collections.defaultdict(list)
for sid, r in species.items():
    chains[int(r['evolution_chain_id'])].append(sid)


def chain_text(sid):
    members = chains[int(species[sid]['evolution_chain_id'])]
    if len(members) == 1:
        return '不會進化'
    children = collections.defaultdict(list)
    roots = []
    for m in sorted(members):
        parent = species[m]['evolves_from_species_id']
        if parent and int(parent) in members:
            children[int(parent)].append(m)
        else:
            roots.append(m)
    lines = []

    def walk(node, prefix):
        kids = children.get(node, [])
        path = prefix + sp_zh[node]
        if not kids:
            lines.append(path)
        for k in kids:
            walk(k, f"{path} →({evo_cond.get(k, '特殊條件')}) ")

    for root in roots:
        walk(root, '')
    return '；'.join(lines)


# ---------- write files ----------
def dump(kind, ident, data):
    os.makedirs(os.path.join(OUT, kind), exist_ok=True)
    with open(os.path.join(OUT, kind, f'{ident}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def multipliers(table, keys):
    out = {}
    for label, want in keys:
        names_ = [type_zh[t] for t, f in table.items() if f == want]
        if names_:
            out[label] = names_
    return out


for sid, sp in species.items():
    pk = default_pokemon[sid]
    pid = int(pk['id'])
    types = [t for _, t in sorted(ptypes[pid])]
    stats = dict(pstats[pid])
    stats['總和'] = sum(stats.values())
    abil = sorted(pabilities[pid])
    normal = [ab_zh[a] for _, a, hidden in abil if not hidden and a in ab_zh]
    hidden = [ab_zh[a] for _, a, h in abil if h and a in ab_zh]
    d = defence(types)
    data = {
        '全國圖鑑編號': sid,
        '名字': sp_zh[sid],
        '英文名': sp_en.get(sid, ''),
        '分類': genus_zh.get(sid, ''),
        '屬性': tn(types),
        '第幾世代登場': int(sp['generation_id']),
        '身高': f"{int(pk['height']) / 10:g} 公尺",
        '體重': f"{int(pk['weight']) / 10:g} 公斤",
        '特性': normal,
    }
    if hidden:
        data['隱藏特性'] = hidden
    data['種族值'] = stats
    data['被攻擊時'] = multipliers(d, [('4倍傷害（超級弱點）', 4), ('2倍傷害（弱點）', 2),
                                  ('0.5倍傷害（抵抗）', 0.5), ('0.25倍傷害', 0.25), ('完全無效', 0)])
    data['進化'] = chain_text(sid)
    if sp['is_legendary'] == '1':
        data['特別'] = '傳說的寶可夢'
    elif sp['is_mythical'] == '1':
        data['特別'] = '幻之寶可夢'
    elif sp['is_baby'] == '1':
        data['特別'] = '寶寶寶可夢'
    if sid in sp_flavor:
        data['圖鑑說明'] = sp_flavor[sid]
    lu = pick_levelup(pid)
    if lu:
        data['升級學會的招式'] = lu
    dump('p', sid, data)

for mid, mv in moves.items():
    if mid not in mv_zh or mid >= 10000:
        continue
    data = {
        '招式': mv_zh[mid],
        '英文名': mv_en.get(mid, ''),
        '屬性': type_zh.get(int(mv['type_id']), '') if mv['type_id'] else '',
        '分類': dmg_class.get(mv['damage_class_id'], ''),
        '威力': int(mv['power']) if mv['power'] else '—',
        '命中': int(mv['accuracy']) if mv['accuracy'] else '必中或不需命中',
        'PP': int(mv['pp']) if mv['pp'] else '—',
    }
    if mv['priority'] and mv['priority'] != '0':
        data['優先度'] = int(mv['priority'])
    if mid in mv_flavor:
        data['說明'] = mv_flavor[mid]
    dump('m', mid, data)

for aid, name in ab_zh.items():
    if aid >= 10000:
        continue
    owners = sorted(set(ability_owners.get(aid, [])))
    data = {'特性': name, '英文名': ab_en.get(aid, '')}
    if aid in ab_flavor:
        data['說明'] = ab_flavor[aid]
    if owners:
        data['擁有這個特性的寶可夢（舉例）'] = [sp_zh[p] for p in owners[:12]]
    dump('a', aid, data)

for t in range(1, NUM_TYPES + 1):
    atk = {d: eff.get((t, d), 1.0) for d in range(1, NUM_TYPES + 1)}
    dfn = {a: eff.get((a, t), 1.0) for a in range(1, NUM_TYPES + 1)}
    examples = [sp_zh[s] for s in sorted(species)
                if t in [x for _, x in ptypes[int(default_pokemon[s]['id'])]]][:12]
    data = {
        '屬性': type_zh[t],
        '英文名': type_en[t],
        f'用{type_zh[t]}屬性招式攻擊時': multipliers(atk, [('效果絕佳（2倍）', 2), ('效果不好（0.5倍）', 0.5),
                                                  ('沒有效果（0倍）', 0)]),
        f'{type_zh[t]}屬性寶可夢被攻擊時': multipliers(dfn, [('弱點（2倍）', 2), ('抵抗（0.5倍）', 0.5),
                                                    ('完全無效（0倍）', 0)]),
        '代表寶可夢（舉例）': examples,
    }
    dump('t', t, data)

# ---------- index ----------
def norm(key):
    key = unicodedata.normalize('NFKC', key).lower()
    return re.sub(r"[\s\-_.'’‘:：·・♀♂()（）]", '', key)


index = {}  # key -> list of refs (dedup, first wins order)


def add(key, ref):
    k = norm(key)
    if not k:
        return
    refs = index.setdefault(k, [])
    if ref not in refs:
        refs.append(ref)


for sid in species:
    for src in (sp_zh, sp_hans, sp_en):
        if sid in src:
            add(src[sid], f'p/{sid}')
for t in range(1, NUM_TYPES + 1):
    for src in (type_zh, type_hans):
        for suffix in ('', '系', '屬性', '屬', '属性', '系屬性'):
            add(src[t] + suffix, f't/{t}')
    add(type_en[t], f't/{t}')
    add(type_en[t] + ' type', f't/{t}')
for mid in mv_zh:
    if mid < 10000:
        for src in (mv_zh, mv_hans, mv_en):
            if mid in src:
                add(src[mid], f'm/{mid}')
for aid in ab_zh:
    if aid < 10000:
        for src in (ab_zh, ab_hans, ab_en):
            if aid in src:
                add(src[aid], f'a/{aid}')

with open(os.path.join(OUT, 'index.txt'), 'w', encoding='utf-8') as f:
    for k in sorted(index):
        f.write(k + '\t' + ','.join(index[k]) + '\n')

print('species', len(species), 'moves', len(os.listdir(os.path.join(OUT, 'm'))),
      'abilities', len(os.listdir(os.path.join(OUT, 'a'))), 'index keys', len(index),
      'index bytes', os.path.getsize(os.path.join(OUT, 'index.txt')))

# ---------- pronunciation index (for speech-recognition homophones) ----------
# pinyin.txt:        "<syllables separated by spaces><TAB>ref" (up to two readings per
#                    polyphonic character, at most 4 variants per name)
# pinyin_chars.txt:  "<syllable><TAB><every CJK character whose default reading it is>"
# Pinyin is used only as an internal key for sound matching; it is never shown or spoken.
import itertools  # noqa: E402

from pypinyin import Style, lazy_pinyin, pinyin  # noqa: E402


def is_cjk(c):
    return 0x3400 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF


display = {}
for sid in species:
    display[f'p/{sid}'] = sp_zh[sid]
for mid in mv_zh:
    display[f'm/{mid}'] = mv_zh[mid]
for aid in ab_zh:
    display[f'a/{aid}'] = ab_zh[aid]
for t in range(1, NUM_TYPES + 1):
    display[f't/{t}'] = type_zh[t]

py_lines = set()
for name_tables, prefix in ((((sp_zh, sp_hans)), 'p'), ((mv_zh, mv_hans), 'm'),
                            ((ab_zh, ab_hans), 'a'), ((type_zh, type_hans), 't')):
    for table in name_tables:
        for ident, name in table.items():
            ref = f'{prefix}/{ident}'
            if ref not in display or ident >= 10000:
                continue
            chars = [c for c in norm(name) if is_cjk(c)]
            if len(chars) < 1 or len(chars) != len(norm(name)):
                continue  # Names with letters or digits are matched by text only
            word = ''.join(chars)
            # The device converts each character with its default reading, so that combination
            # comes first; the phrase reading and other readings of polyphonic characters follow.
            combos = [tuple(lazy_pinyin(c, errors='ignore')[0] for c in chars),
                      tuple(lazy_pinyin(word, errors='ignore'))]
            per_char = [pinyin(c, style=Style.NORMAL, heteronym=True, errors='ignore')[0][:2]
                        for c in chars]
            combos += list(itertools.islice(itertools.product(*per_char), 4))
            for combo in dict.fromkeys(c for c in combos if len(c) == len(chars)):
                py_lines.add(f"{' '.join(combo)}\t{ref}")

# Type keys with suffixes (毒屬性, 毒系) so a misheard "獨屬性" still finds 毒.
for key, refs in index.items():
    if all(is_cjk(c) for c in key) and any(r.startswith('t/') for r in refs):
        syl = ' '.join(lazy_pinyin(c, errors='ignore')[0] for c in key)
        for r in refs:
            if r.startswith('t/'):
                py_lines.add(f"{syl}\t{r}")

with open(os.path.join(OUT, 'pinyin.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(sorted(py_lines)) + '\n')

by_syllable = collections.defaultdict(list)
for code in range(0x4E00, 0xA000):
    c = chr(code)
    s = lazy_pinyin(c, style=Style.NORMAL, errors='ignore')
    if s and s[0].isascii() and s[0].isalpha():
        by_syllable[s[0]].append(c)
with open(os.path.join(OUT, 'pinyin_chars.txt'), 'w', encoding='utf-8') as f:
    for syl in sorted(by_syllable):
        f.write(f"{syl}\t{''.join(by_syllable[syl])}\n")
print('pinyin keys', len(py_lines), 'bytes', os.path.getsize(os.path.join(OUT, 'pinyin.txt')),
      'char table bytes', os.path.getsize(os.path.join(OUT, 'pinyin_chars.txt')),
      'syllables', len(by_syllable))

# ---------- names.txt: number, name, type ids, sprite box, evolution stages ----------
# Stages: "1>2>3"; several Pokémon in one stage are separated by commas ("133>134,135,...").
def chain_stages(sid):
    members = chains[int(species[sid]['evolution_chain_id'])]
    parent = {m: int(species[m]['evolves_from_species_id']) for m in members
              if species[m]['evolves_from_species_id'] and int(species[m]['evolves_from_species_id']) in members}
    stage = {}
    def depth(m):
        if m not in stage:
            stage[m] = 0 if m not in parent else depth(parent[m]) + 1
        return stage[m]
    for m in members:
        depth(m)
    out = []
    for level in range(max(stage.values()) + 1):
        out.append(','.join(str(m) for m in sorted(members) if stage[m] == level))
    return '>'.join(out)


with open(os.path.join(OUT, 'names.txt'), 'w', encoding='utf-8') as f:
    for sid in sorted(species):
        pid = int(default_pokemon[sid]['id'])
        types = ','.join(str(t) for _, t in sorted(ptypes[pid]))
        f.write(f"{sid}\t{sp_zh[sid]}\t{types}\t0,0,96,96\t{chain_stages(sid)}\n")
print('names.txt bytes', os.path.getsize(os.path.join(OUT, 'names.txt')))
