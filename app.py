#!/usr/bin/env python3
"""Flask backend for CipherProbe."""

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from cipherprobe import CIPHERS, HINTS, generate_challenge

# Load .env file if present
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

app = Flask(__name__)

_openai_client = None


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        key = os.environ.get('OPENAI_API_KEY')
        if not key:
            raise RuntimeError('OPENAI_API_KEY not set')
        _openai_client = OpenAI(api_key=key)
    return _openai_client


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/ciphers')
def list_ciphers():
    return jsonify({
        str(k): {
            'name': v['name'],
            'desc': v['desc'],
            'difficulty': v['difficulty'],
        }
        for k, v in CIPHERS.items()
    })


@app.route('/api/encrypt', methods=['POST'])
def encrypt():
    data = request.json
    level = int(data['level'])
    text = data['text']
    cipher = CIPHERS[level]
    return jsonify({
        'result': cipher['encrypt'](text),
        'cipher': cipher['name'],
        'level': level,
    })


@app.route('/api/decrypt', methods=['POST'])
def decrypt():
    data = request.json
    level = int(data['level'])
    text = data['text']
    cipher = CIPHERS[level]
    return jsonify({
        'result': cipher['decrypt'](text),
        'cipher': cipher['name'],
        'level': level,
    })


@app.route('/api/challenge', methods=['POST'])
def challenge():
    data = request.json
    level = int(data['level'])
    text = data['text']
    include_hint = data.get('includeHint', True)
    encrypted, prompt = generate_challenge(level, text, include_hint=include_hint)
    return jsonify({
        'encrypted': encrypted,
        'prompt': prompt,
        'cipher': CIPHERS[level]['name'],
        'level': level,
    })


@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.json
    original = data['original'].strip()
    attempt = data['attempt'].strip()
    if original.lower() == attempt.lower():
        return jsonify({'match': True, 'score': 100.0})
    matches = sum(a == b for a, b in zip(original.lower(), attempt.lower()))
    max_len = max(len(original), len(attempt))
    score = matches / max_len * 100 if max_len else 0
    return jsonify({'match': False, 'score': round(score, 1)})


REASONING_MODELS = {'o1', 'o1-mini', 'o1-preview', 'o3', 'o3-mini', 'o4-mini'}

SYSTEM_MSG = 'You are a cryptanalysis expert. When you decrypt a message, always include a line starting with "DECRYPTED:" followed by the exact decrypted plaintext.'


def call_model(client, model, prompt):
    """Call OpenAI, handling differences between chat and reasoning models."""
    is_reasoning = any(model.startswith(p) for p in ('o1', 'o3', 'o4', 'gpt-5'))
    if is_reasoning:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'user', 'content': SYSTEM_MSG + '\n\n' + prompt},
            ],
            max_completion_tokens=4096,
        )
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': SYSTEM_MSG},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0,
            max_tokens=2048,
        )
    return resp.choices[0].message.content


def extract_and_score(reply, original_text):
    """Extract decrypted attempt from model reply and score it."""
    import re
    attempt = ''
    for line in reply.split('\n'):
        # Strip markdown bold/italic markers before checking
        clean = re.sub(r'[*_`]', '', line).strip()
        if clean.upper().startswith('DECRYPTED:'):
            attempt = clean.split(':', 1)[1].strip().strip('"').strip("'")
            break

    original_lower = original_text.lower().strip()
    attempt_lower = attempt.lower().strip()
    if original_lower == attempt_lower:
        return attempt, True, 100.0
    elif attempt:
        matches = sum(a == b for a, b in zip(original_lower, attempt_lower))
        max_len = max(len(original_lower), len(attempt_lower))
        score = round(matches / max_len * 100, 1) if max_len else 0
        return attempt, False, score
    else:
        return attempt, False, 0.0


@app.route('/api/test', methods=['POST'])
def test_model():
    """Send a cipher challenge to GPT and see if it can crack it."""
    data = request.json
    level = int(data['level'])
    text = data['text']
    model = data.get('model', 'gpt-4o-mini')
    include_hint = data.get('includeHint', True)

    encrypted, prompt = generate_challenge(level, text, include_hint=include_hint)

    try:
        client = get_openai_client()
        reply = call_model(client, model, prompt)
        attempt, match, score = extract_and_score(reply, text)

        return jsonify({
            'level': level,
            'cipher': CIPHERS[level]['name'],
            'difficulty': CIPHERS[level]['difficulty'],
            'original': text,
            'encrypted': encrypted,
            'model': model,
            'model_response': reply,
            'extracted_attempt': attempt,
            'match': match,
            'score': score,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-all', methods=['POST'])
def test_all():
    """Run all 5 cipher levels against the model."""
    data = request.json
    text = data['text']
    model = data.get('model', 'gpt-4o-mini')
    include_hint = data.get('includeHint', True)
    results = []

    client = get_openai_client()

    for level in range(0, 6):
        cipher = CIPHERS[level]
        encrypted, prompt = generate_challenge(level, text, include_hint=include_hint)

        try:
            reply = call_model(client, model, prompt)
            attempt, match, score = extract_and_score(reply, text)

            results.append({
                'level': level,
                'cipher': cipher['name'],
                'difficulty': cipher['difficulty'],
                'encrypted': encrypted,
                'model_response': reply,
                'extracted_attempt': attempt,
                'match': match,
                'score': score,
            })
        except Exception as e:
            results.append({
                'level': level,
                'cipher': cipher['name'],
                'difficulty': cipher['difficulty'],
                'encrypted': encrypted,
                'error': str(e),
                'match': False,
                'score': 0,
            })

    return jsonify({
        'original': text,
        'model': model,
        'includeHint': include_hint,
        'results': results,
    })


CHAT_PROMPTS = {
    'none': '',
    'light': 'Respond in the same format as the user\'s message.',
    'medium': 'The user is communicating in an encoded format. Understand their message and respond to their request using the exact same encoding method.',
}


@app.route('/api/chat', methods=['POST'])
def encrypted_chat():
    """Full roundtrip: encrypt prompt -> send to model -> decrypt response."""
    data = request.json
    level = int(data['level'])
    text = data['text']
    model = data.get('model', 'gpt-4o-mini')
    hint_level = data.get('hintLevel', 'light')  # none, light, medium

    cipher = CIPHERS[level]
    encrypted_prompt = cipher['encrypt'](text)

    # Build the message to send — just the encrypted text + optional nudge
    system_msg = CHAT_PROMPTS.get(hint_level, '')
    user_msg = encrypted_prompt

    try:
        client = get_openai_client()
        is_reasoning = any(model.startswith(p) for p in ('o1', 'o3', 'o4', 'gpt-5'))

        if is_reasoning:
            messages = [{'role': 'user', 'content': (system_msg + '\n\n' + user_msg).strip()}]
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=4096,
            )
        else:
            messages = []
            if system_msg:
                messages.append({'role': 'system', 'content': system_msg})
            messages.append({'role': 'user', 'content': user_msg})
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                max_tokens=2048,
            )

        raw_response = resp.choices[0].message.content

        # Try to decrypt the model's response using the same cipher
        decrypted_response = cipher['decrypt'](raw_response)

        return jsonify({
            'level': level,
            'cipher': cipher['name'],
            'difficulty': cipher['difficulty'],
            'model': model,
            'hintLevel': hint_level,
            'original_prompt': text,
            'encrypted_prompt': encrypted_prompt,
            'raw_response': raw_response,
            'decrypted_response': decrypted_response,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
