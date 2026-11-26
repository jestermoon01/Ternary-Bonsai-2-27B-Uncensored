"""Measure real API decode speed, draft acceptance, wall time and sampled GPU use."""
import argparse
import json
import statistics
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8003'


def call(path, body=None):
    request = urllib.request.Request(BASE + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='mtp1')
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    output_path = ROOT / 'results' / (args.label + '.json')
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'label': args.label,
              'properties': call('/props'), 'tests': [], 'gpu_samples': []}
    stop = threading.Event()

    def monitor():
        while not stop.is_set():
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu,power.draw',
                                         '--format=csv,noheader,nounits'], capture_output=True, text=True,
                                         timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                report['gpu_samples'].append({'utc': datetime.now(timezone.utc).isoformat(),
                                              'memory_util_power': result.stdout.strip()})
            except Exception as error:
                report['gpu_samples'].append({'error': str(error)})
            stop.wait(1)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

    def save():
        output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    def run(name, prompt, thinking=True, budget=1024, measured=True):
        body = {'model': 'bonsai-2.5-27b', 'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': budget, 'temperature': 0, 'seed': 42,
                'chat_template_kwargs': {'enable_thinking': thinking}, 'cache_prompt': False}
        start = time.perf_counter()
        response = call('/v1/chat/completions', body)
        elapsed = time.perf_counter() - start
        timings = response.get('timings', {})
        drafted = timings.get('draft_n', 0)
        accepted = timings.get('draft_n_accepted', 0)
        record = {'name': name, 'measured': measured, 'request': body, 'response': response,
                  'elapsed_seconds': elapsed,
                  'end_to_end_tokens_per_second': response['usage']['completion_tokens'] / elapsed,
                  'draft_acceptance': accepted / drafted if drafted else None}
        report['tests'].append(record)
        save()
        print(json.dumps({'test': name, 'decode_tps': timings.get('predicted_per_second'),
                          'tokens': response['usage']['completion_tokens'], 'seconds': round(elapsed, 3),
                          'acceptance': record['draft_acceptance'], 'timings': timings}), flush=True)
        return response

    try:
        run('warmup', 'Explain briefly why the sky looks blue.', False, 64, False)
        prompts = [
            ('code', 'Implement a Python LRU cache with get and put operations in O(1). '
             'Explain the design, give complete code, and include example tests.', True),
            ('reasoning', 'A warehouse has 120 boxes. Each morning it ships one third of its boxes '
             'and receives 24 new boxes. Find a formula for its inventory after n days, its '
             'long-run limit, and the first day when inventory falls below 80. Explain each step.', True),
            ('prose', 'Write a detailed guide of about 700 words to designing reliable backups '
             'for a small software company. Cover restoration tests, retention, encryption, '
             'offsite copies and operational ownership.', False),
        ]
        for repeat in range(2):
            for name, prompt, thinking in prompts:
                run(f'{name}-{repeat + 1}', prompt, thinking)
        if args.full:
            answer = run('arithmetic', 'What is 37 * 19? Reply only with the integer.', False, 32, False)
            report['arithmetic_passed'] = answer['choices'][0]['message']['content'].strip() == '703'
            prompt = 'Opening code: CEDAR-8142.\n' + (
                'This is filler about ordinary office supplies and daily scheduling.\n' * 1500
            ) + '\nClosing code: MAPLE-7391. Return only the opening and closing codes.'
            answer = run('long-context', prompt, False, 128, False)
            content = answer['choices'][0]['message']['content'] or ''
            report['long_context_passed'] = 'CEDAR-8142' in content and 'MAPLE-7391' in content
            body = {'model': 'bonsai-2.5-27b', 'messages': [{'role': 'user', 'content':
                    'Explain binary search and give a Python implementation.'}],
                    'max_tokens': 256, 'temperature': 0, 'stream': True,
                    'chat_template_kwargs': {'enable_thinking': False}}
            req = urllib.request.Request(BASE + '/v1/chat/completions', data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
            start = time.perf_counter()
            first = None
            chunks = []
            content = []
            done = False
            with urllib.request.urlopen(req, timeout=180) as response:
                for line in response:
                    if not line.startswith(b'data: '):
                        continue
                    data = line[6:].strip()
                    if data == b'[DONE]':
                        done = True
                        break
                    chunk = json.loads(data)
                    chunks.append(chunk)
                    for choice in chunk.get('choices', []):
                        text = choice.get('delta', {}).get('content') or ''
                        if text:
                            if first is None:
                                first = time.perf_counter() - start
                            content.append(text)
            report['streaming'] = {'request': body, 'chunks': chunks, 'content': ''.join(content),
                                   'done': done, 'ttft_seconds': first,
                                   'elapsed_seconds': time.perf_counter() - start}
        measured = [t for t in report['tests'] if t['measured']]
        rates = [t['response']['timings']['predicted_per_second'] for t in measured]
        drafted = sum(t['response']['timings'].get('draft_n', 0) for t in measured)
        accepted = sum(t['response']['timings'].get('draft_n_accepted', 0) for t in measured)
        report['summary'] = {'median_decode_tps': statistics.median(rates), 'min_decode_tps': min(rates),
                             'max_decode_tps': max(rates), 'drafted': drafted, 'accepted': accepted,
                             'draft_acceptance': accepted / drafted if drafted else None}
        print(json.dumps(report['summary']), flush=True)
    finally:
        stop.set()
        thread.join(timeout=6)
        save()


if __name__ == '__main__':
    main()
