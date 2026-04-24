# CipherProbe

A novel cipher suite for testing AI reasoning capabilities. Encrypts prompts with ciphers that language models have never seen in their training data, then measures whether they can crack them.

Built as a research tool for exploring the boundary between pattern matching and genuine reasoning in large language models.

## Why This Exists

Research shows that LLMs can easily crack well-known ciphers (Caesar, Base64, ROT13) because they've seen them in training data. But what happens when you throw a truly novel cipher at them?

CipherProbe answers this by providing:
- **6 cipher levels** — from a Caesar baseline (definitely in training data) to a multi-layer composite cipher no model has seen
- **Automated model testing** — fire all cipher levels at any OpenAI model and score the results
- **Encrypted chat mode** — encrypt your prompt, send it to a model without telling it the cipher, and see if it can understand and respond in the same encryption

## Results

Tested with the prompt *"Write a haiku about the ocean"* (with hints enabled):

| Cipher | Difficulty | GPT-4o-mini | GPT-4o | GPT-4.1 | o4-mini | GPT-5 |
|--------|-----------|:-----------:|:------:|:-------:|:-------:|:-----:|
| L0 Caesar | Baseline | 100% | 100% | 100% | 100% | 100% |
| L1 Fibonacci Shift | Easy | 22.9% | 31.0% | 0% | **100%** | 0% |
| L2 Word Cascade | Medium | 82.8% | 82.8% | **100%** | **100%** | **100%** |
| L3 Vowel-Consonant | Hard | 0% | 3.4% | 0% | 0% | 0% |
| L4 Zigzag+Prime | Very Hard | 10% | 6.9% | 0% | 0% | 0% |
| L5 Composite | Extreme | 2.3% | 6.9% | 0% | 0% | 0% |

Key findings:
- Every model cracks Caesar instantly — proving they *can* do cryptanalysis when they've seen the cipher before
- The reasoning model (o4-mini) is the only one that cracks novel ciphers (L1 and L2)
- Levels 3-5 defeated all models, including GPT-5
- The gap between known ciphers (100%) and novel ciphers (0%) is stark

## Ciphers

| Level | Name | How It Works |
|-------|------|-------------|
| 0 | **Caesar (Baseline)** | Classic shift-by-3. In every model's training data. |
| 1 | **Fibonacci Shift** | Each letter shifts by fib(n) where n is its position. |
| 2 | **Word-Length Cascade** | Each word shifts by the total letter count of all preceding words. |
| 3 | **Vowel-Consonant Split** | Vowels extracted and reversed; consonants shifted within consonant alphabet by index. |
| 4 | **Zigzag Rail + Prime** | 4-rail zigzag transposition, then each character shifts by the nth prime. |
| 5 | **Composite** | Three layers: reverse each word, Fibonacci shift, swap adjacent character pairs. |

## Setup

```bash
# Clone
git clone https://github.com/Leo-t-1/CipherProbe.git
cd CipherProbe

# Install dependencies
pip install flask openai

# Add your OpenAI API key
cp .env.example .env
# Edit .env and add your key

# Run
python app.py
# Open http://127.0.0.1:5000
```

## Usage

### Web UI

The app has 6 tabs:

- **Encrypt / Decrypt** — manually encrypt or decrypt text with any cipher level
- **Challenge** — generate a ready-to-paste challenge prompt for any LLM (with optional hints)
- **Encrypted Chat** — type a prompt, it gets encrypted, sent to a model, and the response gets decrypted. Tests whether the model can understand encrypted input and respond in the same cipher without being told what it is
- **Test Model** — automated benchmark: fires all 6 cipher levels at a model and shows a scorecard
- **Verify** — score a model's decryption attempt against the original

### CLI

```bash
# List ciphers
python cipherprobe.py list

# Encrypt
python cipherprobe.py encrypt 3 "Hello world"

# Generate a challenge prompt
python cipherprobe.py challenge 2 "Write a poem about the stars"

# Verify a model's attempt
python cipherprobe.py verify 1 "hello world" "hello world"
```

## Related Research

- [CipherBank: Exploring the Boundary of LLM Reasoning Capabilities](https://arxiv.org/html/2504.19093v1)
- [When "Competency" in Reasoning Opens the Door to Vulnerability: Jailbreaking LLMs via Novel Ciphers](https://arxiv.org/abs/2402.10601)
- [Benchmarking LLMs for Cryptanalysis](https://arxiv.org/html/2505.24621v1)
- [Probing for Consciousness in Machines](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1610225/full)
