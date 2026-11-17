"""PDF の行（x 位置つき）から、段落と箇条書きの改行を復元する。"""
import re

ROMAN = 'ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ'
# 番号の記号：Ⅰ、１．、（１）、①、（ア）、ア（「ア」の直後がカタカナでないもの。「エレベーター」などの単語は除く）
MARK = re.compile(rf'^([{ROMAN}]+|[０-９0-9]+．|（[０-９0-9]+）|[①-⑳]|（[ア-ン]）|[アイウエオカキクケコ](?=[^ァ-ヶー\s]))')


def width(t):
    """行の幅（全角1、半角0.5で数える）"""
    return sum(0.5 if ord(c) < 0x2000 else 1 for c in t)


def rebuild(rows):
    """rows: [(x, text)] → 段落ごとの行のリスト。
    番号で始まる行は新しい行。それ以外は、前の行が右端まで埋まっていれば続き、
    ただし前の行が「。」で終わり、この行が字下げされていれば新しい段落。"""
    out, prev = [], None
    for x, t in rows:
        t = t.strip()
        m = MARK.match(t)
        if m and (m.group(1)[0] in ROMAN or len(m.group(1)) == 1 and 'ア' <= m.group(1) <= 'ン'):
            t = m.group(1) + ' ' + t[len(m.group(1)):]   # 「Ⅰ 対象確定条件」「ア 未竣工…」のように空白を入れる
        if prev is None or m:
            out.append(t)
        else:
            px, pt = prev
            full = px + width(pt) * 11.04 >= 485
            new_para = pt.endswith('。') and x > px + 5
            if full and not new_para:
                out[-1] += t
            else:
                out.append(t)
        prev = (x, t)
    return out
