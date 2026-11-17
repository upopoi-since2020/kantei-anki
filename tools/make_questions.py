"""登録用の本文ファイルから、原文をそのまま答えにした問題ファイルを作る。

答えは手で書き写さず、「答えの始まり」と「答えの終わり」の語句を指定して、
本文（留意事項の印の行は除く）から切り出す。答えが原文と必ず一致するようにするため。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_items(filename):
    """本文ファイル → {(分類, 項目のタイトル): 本文}（印の行〔留意事項〕は除く）"""
    items, cat, cur = {}, '', None
    for line in (ROOT / filename).read_text(encoding='utf-8').split('\n'):
        if line.startswith('## '):
            cur = (cat, line[3:].strip())
            items[cur] = []
        elif line.startswith('# '):
            cat = line[2:].strip()
        elif cur and line.strip() not in ('〔留意事項〕', '〔/留意事項〕'):
            items[cur].append(line)
    return {k: '\n'.join(v).strip() for k, v in items.items()}


def cut(text, start, end, after=None):
    """start から end までを切り出す。after を指定すると、その語句より後ろから探す"""
    base = text.index(after) if after else 0
    if not after and text.count(start) != 1:
        raise ValueError(f'答えの始まりが1か所に決まりません: {start}（{text.count(start)}か所）')
    s = text.index(start, base)
    return text[s:text.index(end, s) + len(end)]


def write(filename, cat, items, spec):
    """spec: [(項目のタイトル, 問題文, 答えの始まり, 答えの終わり[, この語句の後から探す])]"""
    out, last = ['# 問題'], None
    for title, q, start, end, *after in spec:
        ans = cut(items[(cat, title)], start, end, after[0] if after else None)
        if title != last:
            out.append(f'@ {cat} / {title}')
            last = title
        out += [f'Q {q}', ans]
    (ROOT / filename).write_text('\n'.join(out) + '\n', encoding='utf-8')
    return len(spec)
