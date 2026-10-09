"""鑑定評価基準の目次から Anki 用のデッキ（.apkg）を作る。

目次データは ../index.html の TOC_RAW を読み込む（データの元は1か所にする）。
実行: PYTHONPATH=<genanki のある場所> python3 make_toc_deck.py
"""
import html
import json
import re
from pathlib import Path

import genanki

HERE = Path(__file__).parent
OUT = HERE / '鑑定評価基準_目次.apkg'

# ID は固定（作り直して読み込んでも、同じデッキ・ノートタイプとして更新されるように）
DECK_INPUT_ID = 1_760_000_000_101
DECK_LIST_ID = 1_760_000_000_102
MODEL_INPUT_ID = 1_760_000_000_201
MODEL_LIST_ID = 1_760_000_000_202
DECK_ROOT = '不動産鑑定士::鑑定評価基準 目次'

CSS = """
.card {
  font-family: -apple-system, "Hiragino Sans", "Hiragino Kaku Gothic ProN", sans-serif;
  font-size: 20px; line-height: 1.7; text-align: left;
  color: #1f2328; background: #f6f5f1; padding: 4px 6px;
}
.card.nightMode { color: #e6e6e3; background: #1f2124; }
.crumb { font-size: 14px; color: #6b6f76; line-height: 1.6; }
.crumb span + span::before { content: " ＞ "; }
.q { font-size: 24px; font-weight: 700; margin: 14px 0 10px; }
.no { color: #2f6f5e; margin-right: .4em; }
.nightMode .no { color: #6cc3a6; }
.blank { color: #9a9ea4; font-weight: 400; }
.ask { font-size: 16px; color: #6b6f76; }
#typeans { font-size: 20px; width: 100%; padding: 6px 8px; box-sizing: border-box; }
ol.items { list-style: none; padding: 0; margin: 10px 0 0; }
ol.items li { padding: 3px 8px; border-radius: 6px; }
ol.items li.cur { font-weight: 700; background: #e3efe9; }
.nightMode ol.items li.cur { background: #1f3a32; }
.sub { font-size: 13px; color: #6b6f76; margin-top: 16px; }
"""

MODEL_INPUT = genanki.Model(
    MODEL_INPUT_ID, '鑑定評価基準 目次（見出しを入力）',
    fields=[{'name': 'Path'}, {'name': 'Context'}, {'name': 'Number'}, {'name': 'Answer'}, {'name': 'Siblings'}],
    templates=[{
        'name': '見出しを入力',
        'qfmt': '<div class="crumb">{{Context}}</div>'
                '<div class="q"><span class="no">{{Number}}</span><span class="blank">？</span></div>'
                '{{type:Answer}}',
        'afmt': '<div class="crumb">{{Context}}</div>'
                '<div class="q"><span class="no">{{Number}}</span>{{Answer}}</div>'
                '<hr id="answer">{{type:Answer}}'
                '<div class="sub">同じ階層の見出し</div>{{Siblings}}',
    }],
    css=CSS, sort_field_index=0,
)

MODEL_LIST = genanki.Model(
    MODEL_LIST_ID, '鑑定評価基準 目次（一覧を思い出す）',
    fields=[{'name': 'Path'}, {'name': 'Context'}, {'name': 'Heading'}, {'name': 'Count'}, {'name': 'Items'}],
    templates=[{
        'name': '一覧を思い出す',
        'qfmt': '<div class="crumb">{{Context}}</div>'
                '<div class="q">{{Heading}}</div>'
                '<div class="ask">この中の見出し（{{Count}}つ）を順に思い出す</div>',
        'afmt': '{{FrontSide}}<hr id="answer">{{Items}}',
    }],
    css=CSS, sort_field_index=0,
)


def load_toc():
    src = (HERE.parent / 'index.html').read_text(encoding='utf-8')
    m = re.search(r'const TOC_RAW = (\[.*?\n\]);', src, re.S)
    return [dict(part=p, lv=lv, no=no, name=name) for p, lv, no, name in json.loads(m.group(1))]


def build_tree(rows):
    """各見出しに親・子・パスを付ける。編（総論・各論）は lv=0 の根とする。"""
    roots, stack = [], []
    for r in rows:
        if not stack or stack[0]['part'] != r['part']:
            root = dict(part=r['part'], lv=0, no='', name=r['part'], children=[], parent=None, ancestors=[])
            roots.append(root)
            stack = [root]
        while stack[-1]['lv'] >= r['lv']:
            stack.pop()
        r.update(children=[], parent=stack[-1], ancestors=list(stack))
        stack[-1]['children'].append(r)
        stack.append(r)
        r['path'] = '/'.join([r['part']] + [a['no'] for a in stack[1:]])
    return roots


def label(n):
    return html.escape(f"{n['no']} {n['name']}".strip())


def crumb(nodes):
    return ''.join(f'<span>{label(n)}</span>' for n in nodes)


def items_html(children, current=None):
    lis = [('<li class="cur">' if c is current else '<li>') + label(c) + '</li>' for c in children]
    return '<ol class="items">' + ''.join(lis) + '</ol>'


def main():
    rows = load_toc()
    roots = build_tree(rows)
    deck_input = genanki.Deck(DECK_INPUT_ID, f'{DECK_ROOT}::1 見出しを入力')
    deck_list = genanki.Deck(DECK_LIST_ID, f'{DECK_ROOT}::2 一覧を思い出す')

    for i, r in enumerate(rows):
        tags = [r['part'], f"{r['part']}_{r['ancestors'][1]['no'] if r['lv'] > 1 else r['no']}"]
        deck_input.add_note(genanki.Note(
            model=MODEL_INPUT, guid=genanki.guid_for('toc-input', r['path']), due=i, tags=tags,
            fields=[r['path'], crumb(r['ancestors']), html.escape(r['no']), html.escape(r['name']),
                    items_html(r['parent']['children'], r)],
        ))

    # 子を持つ見出し（と総論・各論そのもの）ごとに一覧カード
    parents = []
    for root in roots:  # 目次の順に：総論 → 総論の各見出し → 各論 → …
        parents.append(root)
        parents.extend(r for r in rows if r['part'] == root['part'] and r['children'])
    for i, p in enumerate(parents):
        path = p.get('path', p['part'])
        deck_list.add_note(genanki.Note(
            model=MODEL_LIST, guid=genanki.guid_for('toc-list', path), due=i, tags=[p['part']],
            fields=[path, crumb(p['ancestors']), label(p), str(len(p['children'])), items_html(p['children'])],
        ))

    genanki.Package([deck_input, deck_list]).write_to_file(OUT)
    print(f'見出しカード {len(deck_input.notes)} 枚 / 一覧カード {len(deck_list.notes)} 枚 → {OUT.name}')


if __name__ == '__main__':
    main()
