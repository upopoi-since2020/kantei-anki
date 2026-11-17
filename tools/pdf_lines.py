"""PDF の各行を、行頭の x 位置つきで JSON に書き出す（段落・箇条書きの復元に使う）。
使い方: python3 pdf_lines.py 入力.pdf 出力.json   （pypdf が必要）
"""
import json
import re
import sys

import pypdf

r = pypdf.PdfReader(sys.argv[1])
lines = []
for pi in range(len(r.pages)):
    frags = {}

    def visit(text, cm, tm, fd, fs):
        if text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            frags.setdefault(round(y, 0), []).append((x, text, fs))

    r.pages[pi].extract_text(visitor_text=visit)
    for y in sorted(frags, reverse=True):
        fr = sorted(frags[y])
        t = ''.join(f[1] for f in fr).strip()
        if re.fullmatch(r'\d+', t):  # ページ番号
            continue
        lines.append([pi + 1, round(fr[0][0], 2), t, fr[0][2]])
json.dump(lines, open(sys.argv[2], 'w'), ensure_ascii=False)
