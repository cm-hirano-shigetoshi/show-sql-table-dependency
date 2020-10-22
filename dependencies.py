import sys
import re

DERIVED_PATTERN = re.compile(r' CREATE TABLE ([^\s\(]+)')
BASE_PATTERN = re.compile(r' (?:FROM|JOIN) ([^\s\(]+)', flags=re.I)
WITH_PATTERN_1 = re.compile(r' WITH (\S+) AS ?\(', flags=re.I)
WITH_PATTERN_2 = re.compile(r'\) ?, ?(\S+) AS ?\(', flags=re.I)


def get_comment_removed_line(line):
    if '--' not in line:
        # '--'がなければそのまま返して終わり
        return line
    else:
        if "'" in line:
            # "'"がなければ、単純に'--'以降がコメント
            return line[:line.find('--')]
        else:
            # "'"があるので、'--'は文字列かもしれない
            # あとで実装する。ひとまず'--'以降はコメントとして扱う
            return line[:line.find('--')]


def get_comment_removed_query(query):
    new_query = ''
    start_pos = -1
    end_pos = 0
    for m in re.finditer(r'(/\*|\*/)', query):
        if m.group(0) == '/*' and start_pos == -1:
            start_pos = m.start()
        elif m.group(0) == '*/' and start_pos > -1:
            new_query += query[end_pos:start_pos]
            end_pos = m.end()
            start_pos = -1
    new_query += query[end_pos:]
    return new_query


def format_query(query):
    # 各単語が単一のスペースで区切られるようにする
    q = ' ' + query + ' '
    q = re.sub(r'\s\s+', ' ', q)

    # IF NOT EXISTS を削除
    q = re.sub(r' IF NOT EXISTS ', ' ', q, flags=re.I)

    # CREATE TABLE/VIEW 系を統一
    q = re.sub(r' CREATE(?:| TEMP) (?:TABLE|VIEW) ',
               ' CREATE TABLE ',
               q,
               flags=re.I)

    # INSERT INTO 系を統一
    q = re.sub(r' INSERT INTO ', ' CREATE TABLE ', q, flags=re.I)
    q = re.sub(r' INSERT ', ' CREATE TABLE ', q, flags=re.I)

    return q


def get_derived_table(query):
    m = re.findall(DERIVED_PATTERN, query)
    assert (len(m) < 2)
    if len(m) == 0:
        return None
    return m[0]


def get_paren_pair_pos(text, start):
    assert (text[start] == '(')
    paren_count = 1
    text = text[start + 1:]
    for m in re.finditer(r'[\(\)]', text):
        if m.group(0) == '(':
            paren_count += 1
        elif m.group(0) == ')':
            paren_count -= 1
            if paren_count == 0:
                end = m.end()
                break
    return end


def one_with(q):
    with_tables = []
    paren_start_pos = q.find('(')
    paren_end_pos = get_paren_pair_pos(q, paren_start_pos)
    q = q[paren_end_pos:]

    # q = '), HOGE AS (...'
    while True:
        # WITH_PATTERN_2 = re.compile(r'\) ?, ?(\S+) AS ?\(', flags=re.I)
        m = re.search(WITH_PATTERN_2, q)
        if m is None:
            break
        with_tables.append(m.group(1))
        paren_start_pos = q.find('(')
        paren_end_pos = get_paren_pair_pos(q, paren_start_pos)
        q = q[paren_end_pos:]
    return with_tables


def get_with_tables(query):
    with_tables = []
    for m in re.finditer(WITH_PATTERN_1, query):
        with_tables.append(m.group(1))
        # q = ' WITH HOGE AS (...'
        q = query[m.start():]
        with_tables.extend(one_with(q))
    return set(with_tables)


def get_base_tables(query):
    m = re.findall(BASE_PATTERN, query)
    return set(m)


def print_line(base_tables, derived_table):
    for base_table in base_tables:
        print('    {} <|-- {}'.format(base_table, derived_table))


def one_query(query):
    # 派生テーブル名を取得
    derived_table = get_derived_table(query)
    if derived_table is None:
        # 派生テーブルを作成しないクエリなら何もしないで終了
        return
    # WITHで作られるテーブル名setを取得
    with_tables = get_with_tables(query)
    # 基底テーブル名setを取得
    base_tables = get_base_tables(query)
    print_line(base_tables - with_tables, derived_table)


def one_file(sql_file):
    queries = None
    with open(sql_file) as f:
        lines = f.readlines()
        # 1行コメントを削除
        lines = [get_comment_removed_line(line) for line in lines]
        # クエリごとの配列に作り替える
        queries = ' '.join(lines).split(';')
        # 複数行コメントを削除
        queries = [get_comment_removed_query(q) for q in queries]
        # クエリをパースしやすい形に加工
        queries = [format_query(q) for q in queries]
    for query in queries:
        one_query(query)


if __name__ == '__main__':
    print("@startuml")
    print("    skinparam padding 10 /'paddingの調整'/")
    print("    left to right direction /'diagramを左から右に伸ばして行くレイアウトにしたい場合'/")
    print("    hide members /'classの属性を消す'/")
    print("    hide circle /'classマークを消す'/")
    for sql_file in sys.argv[1:]:
        one_file(sql_file)
    print("@enduml")
