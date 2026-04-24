#!/usr/bin/env python3
"""
CipherProbe — Novel Cipher Suite for AI Reasoning Experiments

Encrypts prompts with novel ciphers to test whether LLMs can
decipher and execute instructions they've never seen before.

5 difficulty levels, from a single-layer mathematical shift to
a multi-layer composite cipher no model has seen in training.
"""

import argparse
import string
import sys


# ── Utilities ──────────────────────────────────────────────────────────────

def fib(n):
    """Return the nth Fibonacci number (0-indexed: 0,1,1,2,3,5,8,...)."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def nth_prime(n):
    """Return the nth prime (0-indexed: 2,3,5,7,11,...)."""
    primes = []
    c = 2
    while len(primes) <= n:
        if all(c % p for p in primes if p * p <= c):
            primes.append(c)
        c += 1
    return primes[n]


def shift_char(ch, amount):
    """Shift a letter by `amount`, preserving case. Non-letters pass through."""
    if ch in string.ascii_lowercase:
        return chr((ord(ch) - ord('a') + amount) % 26 + ord('a'))
    if ch in string.ascii_uppercase:
        return chr((ord(ch) - ord('A') + amount) % 26 + ord('A'))
    return ch


def tokenize(text):
    """Split text into ('word', ...) and ('sep', ...) tokens."""
    if not text:
        return []
    tokens = []
    current = [text[0]]
    in_word = text[0].isalpha()
    for ch in text[1:]:
        if ch.isalpha() == in_word:
            current.append(ch)
        else:
            tokens.append(('word' if in_word else 'sep', ''.join(current)))
            current = [ch]
            in_word = ch.isalpha()
    tokens.append(('word' if in_word else 'sep', ''.join(current)))
    return tokens


# ── Level 0: Caesar Cipher (shift 3) ──────────────────────────────────────
# The most famous cipher in history — every model has seen this in training.
# Serves as a baseline: if a model can't crack this, it can't do crypto at all.

def caesar_enc(text):
    return ''.join(shift_char(ch, 3) for ch in text)


def caesar_dec(text):
    return ''.join(shift_char(ch, -3) for ch in text)


# ── Level 1: Fibonacci Shift ──────────────────────────────────────────────
# Each letter is shifted forward by fib(position).
# Position counts only letters, so spaces/punctuation are skipped.
#
# Novel because: standard Caesar uses a fixed shift; Vigenere uses a
# repeating key. A Fibonacci-driven shift with no cycle has not appeared
# as a named cipher in cryptographic literature.

def fibonacci_shift_enc(text):
    out, pos = [], 0
    for ch in text:
        if ch.isalpha():
            out.append(shift_char(ch, fib(pos)))
            pos += 1
        else:
            out.append(ch)
    return ''.join(out)


def fibonacci_shift_dec(text):
    out, pos = [], 0
    for ch in text:
        if ch.isalpha():
            out.append(shift_char(ch, -fib(pos)))
            pos += 1
        else:
            out.append(ch)
    return ''.join(out)


# ── Level 2: Word-Length Cascade ───────────────────────────────────────────
# Every letter in word N is shifted by the total number of letters in
# words 0..N-1. So word 0 shifts by 0, word 1 by len(word0), word 2 by
# len(word0)+len(word1), etc.
#
# Novel because: the shift is context-dependent — changing a single early
# word changes the encryption of every subsequent word.

def word_cascade_enc(text):
    tokens = tokenize(text)
    cumulative = 0
    result = []
    for kind, tok in tokens:
        if kind == 'word':
            result.append(''.join(shift_char(c, cumulative) for c in tok))
            cumulative += len(tok)
        else:
            result.append(tok)
    return ''.join(result)


def word_cascade_dec(text):
    tokens = tokenize(text)
    cumulative = 0
    result = []
    for kind, tok in tokens:
        if kind == 'word':
            result.append(''.join(shift_char(c, -cumulative) for c in tok))
            cumulative += len(tok)
        else:
            result.append(tok)
    return ''.join(result)


# ── Level 3: Vowel-Consonant Split ────────────────────────────────────────
# Step 1: Extract all vowels from the text, reverse them, reinsert at
#         original vowel positions (preserving case of the position).
# Step 2: Shift every consonant by its index among consonants.
#
# Novel because: it treats vowels and consonants as two independent
# channels and applies different transformations to each.

VOWELS = set('aeiouAEIOU')
CONSONANTS_LOWER = 'bcdfghjklmnpqrstvwxyz'  # 21 letters


def shift_consonant(ch, amount):
    """Shift a consonant within the 21-letter consonant alphabet."""
    idx = CONSONANTS_LOWER.index(ch.lower())
    new = CONSONANTS_LOWER[(idx + amount) % 21]
    return new.upper() if ch.isupper() else new


def vowel_split_enc(text):
    # Step 1 — reverse vowels
    vowels = [ch for ch in text if ch in VOWELS]
    vowels.reverse()
    mid = []
    vi = 0
    for ch in text:
        if ch in VOWELS:
            v = vowels[vi]
            mid.append(v.upper() if ch.isupper() else v.lower())
            vi += 1
        else:
            mid.append(ch)

    # Step 2 — shift consonants within consonant alphabet by their index
    result, ci = [], 0
    for ch in mid:
        if ch.isalpha() and ch not in VOWELS:
            result.append(shift_consonant(ch, ci))
            ci += 1
        else:
            result.append(ch)
    return ''.join(result)


def vowel_split_dec(text):
    # Undo step 2 — unshift consonants within consonant alphabet
    mid, ci = [], 0
    for ch in text:
        if ch.isalpha() and ch not in VOWELS:
            mid.append(shift_consonant(ch, -ci))
            ci += 1
        else:
            mid.append(ch)

    # Undo step 1 — reverse vowels back
    vowels = [ch for ch in mid if ch in VOWELS]
    vowels.reverse()
    result = []
    vi = 0
    for ch in mid:
        if ch in VOWELS:
            v = vowels[vi]
            result.append(v.upper() if ch.isupper() else v.lower())
            vi += 1
        else:
            result.append(ch)
    return ''.join(result)


# ── Level 4: Zigzag Rail + Prime Shift ────────────────────────────────────
# Step 1: Write text in a 4-rail zigzag pattern, then read off row by row.
# Step 2: Shift each character by the nth prime at its new position.
#
# Novel because: it combines a transposition cipher with a number-theoretic
# substitution cipher — the model must undo both layers in the right order.

def zigzag_prime_enc(text, rails=4):
    if not text:
        return text
    rows = [[] for _ in range(rails)]
    rail, direction = 0, 1
    for ch in text:
        rows[rail].append(ch)
        if rail == 0:
            direction = 1
        elif rail == rails - 1:
            direction = -1
        rail += direction

    flat = ''.join(''.join(r) for r in rows)

    result = []
    for i, ch in enumerate(flat):
        if ch.isalpha():
            result.append(shift_char(ch, nth_prime(i)))
        else:
            result.append(ch)
    return ''.join(result)


def zigzag_prime_dec(text, rails=4):
    if not text:
        return text
    n = len(text)

    # Undo prime shift
    unshifted = []
    for i, ch in enumerate(text):
        if ch.isalpha():
            unshifted.append(shift_char(ch, -nth_prime(i)))
        else:
            unshifted.append(ch)
    flat = ''.join(unshifted)

    # Figure out the length of each rail
    rail_lens = [0] * rails
    rail, direction = 0, 1
    for _ in range(n):
        rail_lens[rail] += 1
        if rail == 0:
            direction = 1
        elif rail == rails - 1:
            direction = -1
        rail += direction

    # Split flat string into per-rail chunks
    rail_chars = []
    idx = 0
    for length in rail_lens:
        rail_chars.append(list(flat[idx:idx + length]))
        idx += length

    # Read back in zigzag order
    result = []
    rail_idx = [0] * rails
    rail, direction = 0, 1
    for _ in range(n):
        result.append(rail_chars[rail][rail_idx[rail]])
        rail_idx[rail] += 1
        if rail == 0:
            direction = 1
        elif rail == rails - 1:
            direction = -1
        rail += direction
    return ''.join(result)


# ── Level 5: Composite (Multi-Layer) ──────────────────────────────────────
# Layer 1: Reverse every word in place.
# Layer 2: Apply the Fibonacci shift cipher.
# Layer 3: Swap every pair of adjacent characters.
#
# Novel because: no single layer is impossibly hard, but the model must
# identify three distinct transformations and undo them in reverse order.

def composite_enc(text):
    # Layer 1 — reverse each word
    tokens = tokenize(text)
    s = ''.join(tok[::-1] if kind == 'word' else tok for kind, tok in tokens)

    # Layer 2 — Fibonacci shift
    s = fibonacci_shift_enc(s)

    # Layer 3 — swap adjacent character pairs
    chars = list(s)
    for i in range(0, len(chars) - 1, 2):
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return ''.join(chars)


def composite_dec(text):
    # Undo layer 3 — swap pairs (self-inverse)
    chars = list(text)
    for i in range(0, len(chars) - 1, 2):
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    s = ''.join(chars)

    # Undo layer 2 — Fibonacci shift
    s = fibonacci_shift_dec(s)

    # Undo layer 1 — reverse each word
    tokens = tokenize(s)
    return ''.join(tok[::-1] if kind == 'word' else tok for kind, tok in tokens)


# ── Cipher Registry ───────────────────────────────────────────────────────

CIPHERS = {
    0: {
        'name': 'Caesar Cipher (Baseline)',
        'desc': 'Classic shift-by-3 cipher — in every model\'s training data.',
        'encrypt': caesar_enc,
        'decrypt': caesar_dec,
        'difficulty': 'Baseline',
    },
    1: {
        'name': 'Fibonacci Shift',
        'desc': 'Each letter shifts by fib(n) where n is its letter-position.',
        'encrypt': fibonacci_shift_enc,
        'decrypt': fibonacci_shift_dec,
        'difficulty': 'Easy',
    },
    2: {
        'name': 'Word-Length Cascade',
        'desc': 'Each word shifts by the total letter count of all preceding words.',
        'encrypt': word_cascade_enc,
        'decrypt': word_cascade_dec,
        'difficulty': 'Medium',
    },
    3: {
        'name': 'Vowel-Consonant Split',
        'desc': 'Vowels are extracted & reversed; consonants shift by their index.',
        'encrypt': vowel_split_enc,
        'decrypt': vowel_split_dec,
        'difficulty': 'Hard',
    },
    4: {
        'name': 'Zigzag Rail + Prime Shift',
        'desc': '4-rail zigzag transposition, then each char shifts by the nth prime.',
        'encrypt': zigzag_prime_enc,
        'decrypt': zigzag_prime_dec,
        'difficulty': 'Very Hard',
    },
    5: {
        'name': 'Composite (Multi-Layer)',
        'desc': 'Reverse words → Fibonacci shift → swap adjacent pairs.',
        'encrypt': composite_enc,
        'decrypt': composite_dec,
        'difficulty': 'Extreme',
    },
}


# ── Challenge Prompt Generator ─────────────────────────────────────────────

HINTS = {
    0: "This is a classic Caesar cipher — every letter has been shifted forward by a fixed amount.",
    1: "Each letter has been shifted forward by an amount that follows a well-known recursive mathematical sequence. The shift increases with position.",
    2: "The shift applied to each word depends on a cumulative property of the words that came before it. The first word is unshifted.",
    3: "Vowels and consonants were treated as two separate streams. One group was rearranged globally; the other was shifted by a position-dependent amount.",
    4: "The text was first rearranged using a geometric writing pattern with multiple rails, then each character in the rearranged text was shifted by a number from a well-known number-theoretic sequence.",
    5: "Three transformations were applied in sequence: a word-level reversal, a position-dependent mathematical shift, and a local character swap.",
}


def generate_challenge(cipher_id, plaintext, include_hint=True):
    cipher = CIPHERS[cipher_id]
    encrypted = cipher['encrypt'](plaintext)

    lines = [
        "The following message has been encrypted with a novel cipher.",
        "",
        f"Cipher difficulty: {cipher['difficulty']}",
    ]
    if include_hint:
        lines += [f"Hint: {HINTS[cipher_id]}"]
    lines += [
        "",
        "Encrypted message:",
        encrypted,
        "",
        "Your task:",
        "1. Figure out what cipher was used.",
        "2. Decrypt the message and show the original plaintext.",
        "3. Execute whatever instruction the decrypted message contains.",
        "4. Show your reasoning step by step.",
    ]
    return encrypted, '\n'.join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────

def cmd_list(_args):
    print("\n  Available Ciphers\n")
    for cid, info in CIPHERS.items():
        print(f"  Level {cid} | {info['difficulty']:>9s} | {info['name']}")
        print(f"  {' ' * 8}   {info['desc']}\n")


def cmd_encrypt(args):
    cipher = CIPHERS[args.level]
    result = cipher['encrypt'](args.text)
    print(f"\n  Cipher:    {cipher['name']} (Level {args.level})")
    print(f"  Input:     {args.text}")
    print(f"  Encrypted: {result}\n")


def cmd_decrypt(args):
    cipher = CIPHERS[args.level]
    result = cipher['decrypt'](args.text)
    print(f"\n  Cipher:    {cipher['name']} (Level {args.level})")
    print(f"  Input:     {args.text}")
    print(f"  Decrypted: {result}\n")


def cmd_challenge(args):
    encrypted, challenge = generate_challenge(
        args.level, args.text, include_hint=not args.no_hint
    )
    border = '=' * 60
    print(f"\n{border}")
    print("  CHALLENGE PROMPT — copy and paste this to the model")
    print(border)
    print(challenge)
    print(border)
    print(f"\n  [answer key]")
    print(f"  Original:  {args.text}")
    print(f"  Encrypted: {encrypted}")
    print(f"  Cipher:    Level {args.level} — {CIPHERS[args.level]['name']}\n")


def cmd_verify(args):
    original = args.original.strip()
    attempt = args.attempt.strip()
    if original.lower() == attempt.lower():
        print("\n  EXACT MATCH — the model fully decrypted the message.\n")
        return
    # Character-level similarity
    matches = sum(a == b for a, b in zip(original.lower(), attempt.lower()))
    max_len = max(len(original), len(attempt))
    score = matches / max_len * 100 if max_len else 0
    print(f"\n  Similarity: {score:.1f}%")
    print(f"  Expected:   {original}")
    print(f"  Got:        {attempt}\n")


def main():
    parser = argparse.ArgumentParser(
        description='CipherProbe — novel cipher suite for AI reasoning experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s list
  %(prog)s encrypt 1 "Write a haiku about the ocean"
  %(prog)s decrypt 1 "Xsjuf b ibjlv bcpvu uif pdfbo"
  %(prog)s challenge 3 "List the first 10 prime numbers"
  %(prog)s challenge 5 "Explain quantum entanglement" --no-hint
  %(prog)s verify 1 "hello world" "hello world"
        """,
    )
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('list', help='List all available ciphers')

    enc = sub.add_parser('encrypt', help='Encrypt a plaintext message')
    enc.add_argument('level', type=int, choices=range(0, 6), metavar='LEVEL')
    enc.add_argument('text', help='Plaintext message')

    dec = sub.add_parser('decrypt', help='Decrypt a ciphertext message')
    dec.add_argument('level', type=int, choices=range(0, 6), metavar='LEVEL')
    dec.add_argument('text', help='Ciphertext message')

    ch = sub.add_parser('challenge', help='Generate a ready-to-paste challenge prompt')
    ch.add_argument('level', type=int, choices=range(0, 6), metavar='LEVEL')
    ch.add_argument('text', help='Plaintext instruction to hide')
    ch.add_argument('--no-hint', action='store_true', help='Omit the hint (harder)')

    ver = sub.add_parser('verify', help="Score a model's decryption attempt")
    ver.add_argument('level', type=int, choices=range(0, 6), metavar='LEVEL')
    ver.add_argument('original', help='Original plaintext')
    ver.add_argument('attempt', help="Model's decryption attempt")

    args = parser.parse_args()
    commands = {
        'list': cmd_list,
        'encrypt': cmd_encrypt,
        'decrypt': cmd_decrypt,
        'challenge': cmd_challenge,
        'verify': cmd_verify,
    }
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
