import sys
import re

DST_PATTERN = re.compile(
    r'(?:CREATE TABLE|CREATE TABLE IF NOT EXISTS|CREATE VIEW|CREATE VIEW IF NOT EXISTS|INSERT INTO|INSERT)\s+([^\s\(]+)',
    flags=re.I)
SRC_PATTERN = re.compile(r'\s(?:FROM|JOIN)\s+([^\s\(]+)', flags=re.I)
WITH_PATTERN_1 = re.compile(r'WITH\s+(\S+)\s+AS\s*\(', flags=re.I)
WITH_PATTERN_2 = re.compile(r'^\s*,\s*(\S+)\s+AS\s*\(', flags=re.I)


def multiple_queries(sql_files):
    sqls = []
    for sql in sql_files:
        sqls.extend(sql.split(';'))
    return sqls


def remove_comment(sql):
    # 複数行のコメント削除
    new_sql = ''
    start_pos = -1
    end_pos = 0
    for m in re.finditer(r'(/\*|\*/)', sql):
        if m.group(0) == '/*' and start_pos == -1:
            start_pos = m.start()
        elif m.group(0) == '*/' and start_pos > -1:
            new_sql += sql[end_pos:start_pos]
            end_pos = m.end()
            start_pos = -1
    new_sql += sql[end_pos:]

    # 単一行コメント削除
    lines = new_sql.split('\n')
    for i in range(len(lines)):
        line = lines[i]
        # コメント部分を除外
        p = line.find('--')
        if p >= 0:
            line = line[:p]
        lines[i] = line
    return '\n'.join(lines)


def destination(sql):
    m = re.findall(DST_PATTERN, sql)
    if len(m) == 0:
        return None
    elif len(m) != 1:
        raise ValueError
    return m[0]


def get_paren_pair_pos(text):
    (start, end) = (-1, -1)
    paren_count = 0
    for m in re.finditer(r'[\(\)]', text):
        if m.group(0) == '(':
            if paren_count == 0:
                start = m.start()
            paren_count += 1
        elif m.group(0) == ')':
            paren_count -= 1
            if paren_count == 0:
                end = m.end()
                break
    return (start, end)


def get_next_with_names(text):
    names = []
    match = re.search(WITH_PATTERN_1, text)
    if match is None:
        return ([], '')
    names.append(match.group(1))
    text = text[match.end() - 1:]
    while True:
        _, end_paren_pos = get_paren_pair_pos(text)
        text = text[end_paren_pos + 1:]
        m = re.search(WITH_PATTERN_2, text)
        if m is None:
            break
        else:
            names.append(m.group(1))
            text = text[m.end() - 1:]
    return (names, text)


def get_with_names(sql):
    text = sql
    with_names = []
    while len(text) > 0:
        (names, text) = get_next_with_names(text)
        with_names.extend(names)
    return with_names


def source(sql):
    with_names = get_with_names(sql)
    m = re.findall(SRC_PATTERN, sql)
    src = set(m) - set(with_names)
    return src


def extract_dependencies(sql):
    dst = destination(sql)
    if dst is None:
        return None
    else:
        src = source(sql)
        return (dst, src)


def print_uml_str(dependencies):
    lines = {}
    for k, v in dependencies.items():
        for t in v:
            lines["{} <|-- {}".format(t, k)] = 1
    print('''
    @startuml
    skinparam padding 10 /'paddingの調整'/
    left to right direction /'diagramを左から右に伸ばして行くレイアウトにしたい場合'/
    hide members /'classの属性を消す'/
    hide circle /'classマークを消す'/
    {}
    @enduml
    '''.format('\n    '.join(lines.keys())))


if __name__ == '__main__':
    sql_files = []
    for arg in sys.argv[1:]:
        with open(arg) as f:
            sql_files.append(' '.join(f.readlines()))

    sql_files = [remove_comment(sql) for sql in sql_files]
    sqls = multiple_queries(sql_files)

    dependencies = {}
    for sql in sqls:
        d = extract_dependencies(sql)
        if d is not None:
            dependencies[d[0]] = d[1]

    print_uml_str(dependencies)
