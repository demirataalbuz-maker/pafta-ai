"""Query mutations against actual task tests; proven equivalents stay visible.

The bounded equivalence rules below are semantic, not corpus-output guesses:
Lucene's unbounded range inclusion has no endpoint to exclude; and classic
OR-default QueryParser leaves both operands required when their *other*
adjacent conjunctions at the same parenthesis level are AND. No general
query equivalence is claimed. Every mutant is executed, including these.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get


def lexical_mask(source, dialect):
    """Keep operator positions, blank quoted/regexp/escaped literal contents."""
    result = list(source)
    at = 0
    while at < len(source):
        start = at
        if source[at] == '\\':
            at = min(at + 2, len(source))
        elif source.startswith('"""', at) and dialect == 'eql':
            end = source.find('"""', at + 3)
            at = len(source) if end < 0 else end + 3
        elif source[at] in ('"', "'"):
            quote = source[at]
            at += 1
            while at < len(source):
                if source[at] == '\\':
                    at += 2
                elif source[at] == quote:
                    at += 1
                    break
                else:
                    at += 1
        elif source[at] == '/' and dialect == 'lucene':
            at += 1
            while at < len(source):
                if source[at] == '\\':
                    at += 2
                elif source[at] == '/':
                    at += 1
                    break
                else:
                    at += 1
        else:
            at += 1
            continue
        for pos in range(start, min(at, len(source))):
            result[pos] = '\n' if source[pos] == '\n' else ' '
    return ''.join(result)


def range_matches(source):
    # Quoted timestamps and regex literal character classes cannot introduce
    # fake TO operators. Endpoints are recovered from the original positions.
    mask = lexical_mask(source, 'lucene')
    return re.finditer(r'(\[|\{)[^\[\]{}]*\bTO\b[^\[\]{}]*(\]|\})', mask)


def operator_mask(source, dialect):
    mask = list(lexical_mask(source, dialect))
    if dialect == 'lucene':
        # QueryParser's range lexical state accepts words such as AND as a
        # bound. Those are data, not Boolean connectors or proof evidence.
        for match in range_matches(source):
            for at in range(match.start(), match.end()):
                mask[at] = '\n' if source[at] == '\n' else ' '
    return ''.join(mask)


def mutations(source, dialect):
    mask = operator_mask(source, dialect)
    seen = {source}
    def changed(a, b, replacement, label):
        value = source[:a] + replacement + source[b:]
        if value not in seen:
            seen.add(value)
            return label, value
    for match in re.finditer(r'(?<![\w.@:\-])(?:AND|OR|and|or)(?![\w.@:\-])|>=|<=|(?<![<>!=])[<>](?!=)', mask):
        text = match[0]
        replacement = {'AND':'OR', 'OR':'AND', 'and':'or', 'or':'and', '>=':'>', '<=':'<', '>':'>=', '<':'<='}[text]
        result = changed(*match.span(), replacement, f'{text} -> {replacement} @{match.start()}')
        if result:
            yield result
    for match in re.finditer(r'(?<![\w.@:\-])(?:NOT|not)\s+', mask):
        result = changed(*match.span(), '', f'NOT removed @{match.start()}')
        if result:
            yield result
    if dialect == 'lucene':
        for match in range_matches(source):
            for position, old in ((match.start(), match[1]), (match.end()-1, match[2])):
                replacement = {'[':'{', '{':'[', ']':'}', '}':']'}[old]
                result = changed(position, position+1, replacement, f'range {old} -> {replacement} @{position}')
                if result:
                    yield result
        for match in re.finditer(r'~([0-9]+)(?![0-9.])', mask):
            number = int(match[1])
            for n in (number-1, number+1):
                if 0 <= n <= 2:
                    result = changed(*match.span(), '~'+str(n), f'slop/fuzzy {number} -> {n} @{match.start()}')
                    if result:
                        yield result
    if dialect == 'eql':
        for match in re.finditer(r'\bmaxspan\s*=\s*(\d+)(ms|s|m|h|d)\b', mask):
            milliseconds = int(match[1]) * {'ms':1,'s':1000,'m':60000,'h':3600000,'d':86400000}[match[2]]
            # Unit-sized changes miss off-by-one bugs. Replace the full duration
            # with a valid millisecond literal at the exact adjacent boundary.
            for delta in (-1, 1):
                value = milliseconds + delta
                if value > 0:
                    result = changed(match.start(1), match.end(2), str(value)+'ms',
                                     f'maxspan {milliseconds}ms -> {value}ms @{match.start(1)}')
                    if result:
                        yield result
        for match in re.finditer(r'==|:', mask):
            if source[match.end():].lstrip().startswith('"'):
                replacement = ':' if match[0] == '==' else '=='
                result = changed(*match.span(), replacement, f'case operator {match[0]} -> {replacement} @{match.start()}')
                if result:
                    yield result
        for match in re.finditer(r'(?<![\w.@:\-])(?:in|like)~?(?![\w.@:\-])', mask):
            text = match[0]
            if text in ('in','like') and source[match.end():].startswith('~'):
                continue
            replacement = text[:-1] if text.endswith('~') else text+'~'
            result = changed(*match.span(), replacement, f'case operator {text} -> {replacement} @{match.start()}')
            if result:
                yield result
        for match in re.finditer(r'\buntil\s*\[[^\]]*\]', mask):
            result = changed(*match.span(), '', f'until removed @{match.start()}')
            if result:
                yield result
        for match in re.finditer(r'!\s*(?=\[)', mask):
            result = changed(*match.span(), '', f'missing stage made positive @{match.start()}')
            if result:
                yield result


def single_clause(fragment):
    """Conservative complete-clause check, never an implicit-OR term list.

    This is only a precondition for the narrow proof, not a query parser. The
    actual mutant still runs through the native parser and the task tests.
    """
    value = fragment.strip()
    if value.startswith('NOT '):
        value = value[4:].strip()
    field = re.match(r'[A-Za-z@][A-Za-z0-9_.@-]*:\s*', value)
    if field:
        value = value[field.end():]
    elif not value.startswith('('):
        return False
    if not value:
        return False
    if value.startswith('('):
        mask = operator_mask(value, 'lucene')
        depth = 0
        for i,ch in enumerate(mask):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return i == len(value)-1
        return False
    if value[0] in '[{':
        matches = list(range_matches(value))
        return len(matches) == 1 and matches[0].span() == (0,len(value))
    if value.startswith('"'):
        return bool(re.fullmatch(r'"(?:\\.|[^"\\])*"(?:~[0-9]+)?',value))
    if value.startswith('/'):
        return bool(re.fullmatch(r'/(?:\\.|[^/\\])+/',value))
    return bool(re.fullmatch(r'(?:\\.|[^\s()])+',value))


def equivalence_reason(source, mutant, dialect):
    if dialect != 'lucene':
        return None
    for match in range_matches(source):
        interior = source[match.start()+1:match.end()-1]
        # TO is outside quoted strings by range_matches; the same source slice
        # can contain no other syntactic TO in the currently supported grammar.
        split = re.search(r'\bTO\b', lexical_mask(interior, 'lucene'))
        if split is None:
            continue
        ends = (interior[:split.start()].strip(), interior[split.end():].strip())
        for position, token, bound in ((match.start(), match[1], ends[0]), (match.end()-1, match[2], ends[1])):
            replacement = {'[':'{', '{':'[', ']':'}', '}':']'}[token]
            if bound == '*' and source[:position]+replacement+source[position+1:] == mutant:
                return 'Lucene range endpoint is unbounded *; its inclusive/exclusive bracket cannot change membership.'
    mask = operator_mask(source, 'lucene')
    # Only a single AND -> OR edit is eligible, in a flat explicit-AND run.
    # Parenthesis scopes are tracked structurally. OR-default QueryParser marks
    # both neighboring operands MUST via their other adjacent AND, so replacing
    # this middle connector has no effect. Unary +/- are deliberately excluded.
    stack = [0]
    next_scope = 1
    operators = {}
    for token in re.finditer(r'[()]|(?<![\w.@:\-])(?:AND|OR)(?![\w.@:\-])', mask):
        if token[0] == '(':
            stack.append(next_scope); next_scope += 1
        elif token[0] == ')':
            if len(stack) > 1:
                stack.pop()
        else:
            operators.setdefault(stack[-1], []).append(token)
    for tokens in operators.values():
        for i in range(1,len(tokens)-1):
            left, target, right = tokens[i-1:i+2]
            if all(t[0] == 'AND' for t in (left,target,right)):
                segment = mask[left.end():right.start()]
                if '+' in segment or '-' in segment:
                    continue
                if not single_clause(source[left.end():target.start()]) or not single_clause(source[target.end():right.start()]):
                    continue
                if source[:target.start()]+'OR'+source[target.end():] == mutant:
                    return 'Classic Lucene OR-default QueryParser: both operands remain MUST through the adjacent AND on their other sides.'
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('lessons', nargs='*')
    parser.add_argument('--json', dest='report')
    args = parser.parse_args()
    lib = Library()
    tasks = [(f'{lid}:{i}', step) for lid in lib.outline('elastic')['order'] if not args.lessons or lid in args.lessons
             for i, step in enumerate(lib.lesson('elastic', lid)['steps']) if step['kind'] == 'gorev'
             and json.loads(step.get('stdin', '{}')).get('backend') != 'elastic']
    if args.lessons and not tasks:
        parser.error('Gerçek API dersleri için tools/audit_elastic_native.py kullanın; bu araç EL01–EL19 içindir.')
    runner = get('elastic')
    with ThreadPoolExecutor(max_workers=4) as pool:
        baseline = list(pool.map(lambda pair: (pair[0], runner.test(pair[1]['solution'], pair[1])), tasks))
    invalid = [(ref,result) for ref,result in baseline if result['status'] != 'pass']
    if invalid:
        for ref,result in invalid:
            print('ORIGINAL FAILED',ref,result)
        return 1
    jobs = [(ref,step,label,query) for ref,step in tasks for label,query in mutations(step['solution'],step['meta']['dil'])]
    def check(job):
        ref,step,label,query = job
        return {'task':ref,'mutation':label,'query':query,'result':runner.test(query,step),
                'equivalence_reason':equivalence_reason(step['solution'],query,step['meta']['dil'])}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check,jobs))
    survivors = [r for r in results if r['result']['status']=='pass' and not r['equivalence_reason']]
    equivalent = [r for r in results if r['result']['status']=='pass' and r['equivalence_reason']]
    errors = [r for r in results if r['result']['status'] not in ('pass','fail')]
    failed = [r for r in results if r['result']['status']=='fail']
    # A counterexample disproves the bounded classification and must not be hidden.
    wrong_proof = [r for r in failed if r['equivalence_reason']]
    print(f'{len(tasks)} solutions pass; {len(results)} mutations; {len(failed)} fail; {len(equivalent)} proven-equivalent; {len(survivors)} survivors; {len(errors)} errors')
    for row in equivalent+survivors+errors:
        print('EQUIVALENT' if row in equivalent else row['result']['status'].upper(),row['task'],row['mutation'],repr(row['query']))
        if row['equivalence_reason']:
            print('  Reason:',row['equivalence_reason'])
    for row in wrong_proof:
        print('EQUIVALENCE PROOF CONTRADICTED',row['task'],row['mutation'])
    if args.report:
        Path(args.report).parent.mkdir(parents=True,exist_ok=True)
        Path(args.report).write_text(json.dumps({'tasks':len(tasks),'baseline':baseline,'summary':{'mutations':len(results),'fail':len(failed),'equivalent':len(equivalent),'survivors':len(survivors),'errors':len(errors)},'mutations':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return bool(survivors or errors or wrong_proof)


if __name__ == '__main__':
    sys.exit(main())
