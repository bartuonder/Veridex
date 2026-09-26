---
language:
- en
license: cc-by-4.0
base_model: microsoft/deberta-v3-base
library_name: transformers
pipeline_tag: question-answering
tags:
- question-answering
- extractive-qa
- legal
- legal-nlp
- contract-review
- contract-analysis
- cuad
- deberta-v3
datasets:
- theatticusproject/cuad-qa
metrics:
- exact_match
- f1
model-index:
- name: Veridex-QA
  results:
  - task:
      type: question-answering
      name: Extractive Question Answering
    dataset:
      name: CUAD (Contract Understanding Atticus Dataset)
      type: theatticusproject/cuad-qa
      split: test
    metrics:
    - type: f1
      value: 87.06
      name: SQuAD v2 F1
    - type: exact_match
      value: 83.98
      name: SQuAD v2 Exact Match
---

# Veridex-QA

Extractive question answering model that locates **risk-bearing clauses in commercial contracts**. Given a contract and a clause-category question, it returns the exact text span containing that clause, or abstains when the clause is absent.

Fine-tuned from [`microsoft/deberta-v3-base`](https://huggingface.co/microsoft/deberta-v3-base) on the [CUAD](https://www.atticusprojectai.org/cuad) dataset (510 commercial contracts, 41 clause categories, expert-annotated by lawyers).

The model backs the clause-detection stage of Veridex, a contract review service that flags clauses such as termination for convenience, liability caps, automatic renewal, exclusivity, and change of control.

## Intended use

Surfacing clauses that a reviewer should read, over contract types including supply, distribution, license, service, NDA, and affiliate agreements.

This model is a **triage aid, not legal advice.** It narrows where a human should look; it does not decide whether a clause is acceptable. Do not use it as the sole basis for a contractual decision.

## Usage

Contracts are far longer than the 384-token window, so inference requires a sliding window and the no-answer (CLS) comparison that the model was trained with:

```python
import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer

model_id = "REPLACE_WITH_REPO_ID"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForQuestionAnswering.from_pretrained(model_id).eval()

question = 'Highlight the parts of this contract related to "Termination For Convenience".'
contract = open("contract.txt", encoding="utf-8").read()

encoded = tokenizer(
    question,
    contract,
    truncation="only_second",
    max_length=384,
    stride=128,
    return_overflowing_tokens=True,
    return_offsets_mapping=True,
    padding="max_length",
    return_tensors="pt",
)
sequence_ids = [encoded.sequence_ids(i) for i in range(len(encoded["input_ids"]))]
offsets = encoded.pop("offset_mapping")
encoded.pop("overflow_to_sample_mapping")

with torch.no_grad():
    output = model(**encoded)

best_score, best_span, null_score = -1e9, "", 1e9
for window in range(output.start_logits.shape[0]):
    start_logits, end_logits = output.start_logits[window], output.end_logits[window]
    null_score = min(null_score, float(start_logits[0] + end_logits[0]))
    positions = [i for i, sid in enumerate(sequence_ids[window]) if sid == 1]
    for start in positions:
        for end in positions:
            if end < start or end - start > 256:
                continue
            score = float(start_logits[start] + end_logits[end])
            if score > best_score:
                best_score = score
                best_span = contract[int(offsets[window][start][0]) : int(offsets[window][end][1])]

print(best_span if best_score > null_score else "clause not present")
```

Questions must follow the CUAD phrasing, `Highlight the parts of this contract related to "<Category>".`, because the model learned the association between that phrasing and each of the 41 categories.

## Evaluation

Evaluated on the official CUAD test split: **102 held-out contracts, 4,182 questions, 195,805 sliding windows.** No test contract appears in training.

| Metric | Score |
|---|---|
| F1 | **87.06** |
| Exact match | **83.98** |
| F1 on answerable questions | 83.52 |
| Exact match on answerable questions | 73.15 |
| Correct abstention on absent clauses | 88.56 |
| Recall at 80% precision | 59.24 |

`Recall at 80% precision` is a deployment-oriented metric: sweeping the answerability threshold, it reports how many present clauses are caught while keeping false alarms at or below 20%. It matters more than raw F1 for review workflows, where a missed clause costs far more than an extra clause to read.

### Per-category results

Strongest and weakest of the 41 categories by F1:

| Strongest | F1 | | Weakest | F1 |
|---|---|---|---|---|
| Governing Law | 97.39 | | Effective Date | 61.93 |
| Insurance | 94.80 | | Post-Termination Services | 67.44 |
| Expiration Date | 91.97 | | Termination For Convenience | 67.98 |
| No-Solicit Of Employees | 98.35 | | Non-Transferable License | 73.94 |
| Joint IP Ownership | 97.43 | | Change Of Control | 75.12 |

Categories with crisp lexical anchors (governing law, insurance) score highest. Categories requiring the model to distinguish near-identical wording score lowest: `Effective Date` versus `Agreement Date` versus `Expiration Date` are frequently confused, and `Termination For Convenience` must be separated from termination for cause. Notably `Termination For Convenience` reaches 90.84 F1 on the questions where the clause is actually present, so its low aggregate score comes from false positives rather than misses.

### Interpreting these numbers

Two properties of the CUAD test split inflate F1 relative to a stricter single-answer setting, and both should be understood before comparing against other numbers:

Answerable test questions carry **2.12 accepted gold spans on average** (up to 19), and SQuAD scoring credits the best match among them. On a single-gold validation split carved out of the training contracts, the same checkpoint scores 68.30 F1 / 59.00 EM. Only **29.7%** of test questions are answerable, and abstention is the easier sub-task, which lifts the aggregate further.

These are standard SQuAD v2 metrics, not the precision-recall AUC used as the headline metric in the original CUAD paper, so they are not directly comparable to that publication.

## Training

| | |
|---|---|
| Base model | `microsoft/deberta-v3-base` (183.8M parameters) |
| Method | full fine-tuning, no adapters |
| Epochs | 4 (22,816 optimizer steps) |
| Learning rate | 3e-5, linear decay, 10% warmup |
| Batch size | 16 |
| Optimizer | AdamW, weight decay 0.01 |
| Sequence length | 384, doc stride 128 |
| Precision | bf16 autocast, fp32 master weights |
| Hardware | single RTX 4070 SUPER (12GB) |
| Checkpoint selection | best validation F1, contract-disjoint split |

CUAD contracts average ~10,400 tokens, so each question expands to ~41 windows and the vast majority contain no answer. Keeping every window would mean ~920,000 training features per epoch. Training therefore keeps all answer-bearing windows plus **4 sampled empty windows per question**, reducing the epoch to 91,256 features while preserving every positive example.

Full fine-tuning used fp32 master weights deliberately: the published checkpoint is stored in fp16, and training directly from fp16 weights makes AdamW's second-moment update collapse to NaN on the first optimizer step.

## Limitations

English-language contracts only, drawn from US commercial agreements filed with the SEC; performance on other jurisdictions, languages, or contract styles is untested. Predictions are single-span per question, so a clause split across distant sections may be partially captured. The dominant error mode is **false positives** — among the 200 worst test predictions, 164 were spans returned for clauses that were absent, against 33 missed clauses — so a confidence threshold should be tuned for the target workflow rather than left at the default.

## License and attribution

Released under **CC BY 4.0**, following CUAD. The base model `microsoft/deberta-v3-base` is MIT licensed.

```bibtex
@article{hendrycks2021cuad,
  title={CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review},
  author={Hendrycks, Dan and Burns, Collin and Chen, Anya and Ball, Spencer},
  journal={NeurIPS Datasets and Benchmarks},
  year={2021}
}
```
