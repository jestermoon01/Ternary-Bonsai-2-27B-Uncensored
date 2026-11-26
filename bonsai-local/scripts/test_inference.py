"""Exercise the real local API; save full requests, outputs and backend timings."""
import ast
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = 'http://127.0.0.1:8003'
MODEL = 'bonsai-2-27b-uncensored'
OUT = Path(__file__).resolve().parents[1] / 'results' / 'inference.json'


def request(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response)


def check_code(text):
    source = text.split('```python')[-1].split('```')[0].strip() if '```' in text else text.strip()
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'sum_even')
    # Evaluate only a narrowly allowed pure expression, never arbitrary model code.
    if len(function.body) != 1 or not isinstance(function.body[0], ast.Return):
        return False
    allowed = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Call,
               ast.Name, ast.Load, ast.GeneratorExp, ast.comprehension, ast.Store,
               ast.Compare, ast.BinOp, ast.Mod, ast.Eq, ast.Constant, ast.ListComp)
    if any(not isinstance(n, allowed) for n in ast.walk(tree)):
        return False
    if any(isinstance(n, ast.Call) and (not isinstance(n.func, ast.Name) or n.func.id != 'sum')
           for n in ast.walk(tree)):
        return False
    namespace = {'__builtins__': {}, 'sum': sum}
    exec(compile(tree, '<model-output>', 'exec'), namespace)
    return all(namespace['sum_even'](values) == expected for values, expected in
               [([], 0), ([1, 2, 3, 4], 6), ([-4, -3, 0, 8], 4)])


def main():
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'model': MODEL,
              'adapter_scale': 1.5, 'thinking': False, 'health': request('/health'),
              'models': request('/v1/models'), 'tests': []}
    tests = [
        ('arithmetic', 'What is 37 * 19? Reply with only the integer.', 32, lambda s: s.strip() == '703'),
        ('coding', 'Write a Python function sum_even(numbers) that returns the sum of even integers. '
         'Use one return statement with sum and a generator expression. Output only Python code.', 192, check_code),
        ('explanation', 'Explain how a CPU and GPU differ, in about 150 words.', 256,
         lambda s: 'CPU' in s and 'GPU' in s and len(s.split()) > 60),
        ('context_recall', 'Remember the opening code: CEDAR-8142.\n' +
         ('This is filler text about ordinary office supplies and daily scheduling.\n' * 1500) +
         '\nThe closing code is MAPLE-7391. Return only the opening and closing codes.',
         64, lambda s: 'CEDAR-8142' in s and 'MAPLE-7391' in s),
    ]
    for name, prompt, tokens, check in tests:
        body = {'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': tokens, 'temperature': 0, 'seed': 42,
                'chat_template_kwargs': {'enable_thinking': False}}
        start = time.perf_counter()
        result = request('/v1/chat/completions', body)
        elapsed = time.perf_counter() - start
        text = result['choices'][0]['message'].get('content') or ''
        try:
            passed = check(text)
        except Exception:
            passed = False
        record = {'name': name, 'request': body, 'response': result,
                  'elapsed_seconds': elapsed, 'passed': passed}
        report['tests'].append(record)
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'test': name, 'passed': passed, 'seconds': round(elapsed, 2),
                          'usage': result.get('usage'), 'timings': result.get('timings'),
                          'output': text[:1000]}), flush=True)
    body = {'model': MODEL, 'messages': [{'role': 'user', 'content': 'Reply with exactly: stream works'}],
            'max_tokens': 32, 'temperature': 0, 'stream': True,
            'chat_template_kwargs': {'enable_thinking': False}}
    start = time.perf_counter()
    first = None
    pieces = []
    done = False
    req = urllib.request.Request(BASE + '/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            data = line[6:].strip()
            if data == b'[DONE]':
                done = True
                break
            chunk = json.loads(data)
            for choice in chunk.get('choices', []):
                content = choice.get('delta', {}).get('content') or ''
                if content:
                    if first is None:
                        first = time.perf_counter() - start
                    pieces.append(content)
    output = ''.join(pieces)
    report['streaming'] = {'request': body, 'output': output, 'done': done,
                           'ttft_seconds': first, 'elapsed_seconds': time.perf_counter() - start,
                           'passed': done and output.strip() == 'stream works'}
    OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['streaming']), flush=True)
    if not all(t['passed'] for t in report['tests']) or not report['streaming']['passed']:
        raise SystemExit('Some inference checks failed; inspect results/inference.json')


if __name__ == '__main__':
    main()
