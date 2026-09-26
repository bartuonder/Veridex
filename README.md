# Veridex

Veridex extracts high-risk clauses from contracts and scores them by severity. Upload a lease, supply agreement, NDA, or service contract; the API runs a fine-tuned extractive QA model over a CUAD-style clause catalog and returns the span, risk level, and a document-level summary.

The current catalog covers 16 clause types, including termination for convenience, liability caps, auto-renewal, exclusivity, IP assignment, and governing law.

## Model

Fine-tuned **DeBERTa-v3-base** on [CUAD](https://www.atticusprojectai.org/cuad) (`theatticusproject/cuad-qa`), published at:

**https://huggingface.co/Bartu0nder/Veridex-QA-cuad-deberta-v3**

| Split | F1 | Exact match | Notes |
| --- | --- | --- | --- |
| Validation | 68.30 | 59.00 | Best checkpoint by `eval_f1` |
| Test (`null_score_diff_threshold=-2.0`) | 87.96 | 84.91 | Default used by the API |
| Test (`null_score_diff_threshold=-5.0`) | 89.03 | 86.49 | Previous operating point |

Training is full fine-tuning (no LoRA). Runs are tracked in MLflow and the best checkpoint is registered as `Veridex-QA` with the `staging` alias.

## Architecture

```
Contract text
    -> FastAPI POST /analyze
    -> sliding-window DeBERTa QA (max_seq_length=384, stride=128)
    -> null-score gate (threshold -2.0)
    -> clause spans + risk summary
```

| Layer | Role |
| --- | --- |
| `training/` | CUAD preprocessing, Trainer loop, SQuAD-v2 postprocessing, evaluation, MLflow registry |
| `api/` | FastAPI service, Pydantic schemas, model loader, clause catalog, risk aggregation |
| `scripts/` | Hugging Face model card and hub upload |

Default inference source is the local MLflow registry (`Veridex-QA@staging`). If that is missing, set `VERIDEX_MODEL_SOURCE=local` and point `VERIDEX_LOCAL_MODEL_PATH` at a downloaded copy of the Hub checkpoint. `mock` is a keyword fallback for development when no weights are available.

## Repository layout

```
api/           FastAPI app, routers, inference services
training/      Fine-tuning, metrics, evaluation, registry
scripts/       Hub publishing
requirements.txt
training/config.yaml
```

## Setup

Python 3.11+ and a CUDA GPU are recommended for training and live inference. CPU works for the mock path and small documents.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Environment

Settings are read from `VERIDEX_*` variables. `.env` is gitignored; copy the block below and export the keys you need.

```env
VERIDEX_MODEL_SOURCE=registry
VERIDEX_REGISTERED_MODEL_NAME=Veridex-QA
VERIDEX_MODEL_ALIAS=staging
VERIDEX_LOCAL_MODEL_PATH=outputs/veridex-qa/best-model
VERIDEX_MLFLOW_TRACKING_URI=sqlite:///mlflow.db
VERIDEX_NULL_SCORE_DIFF_THRESHOLD=-2.0
VERIDEX_INFERENCE_DEVICE=auto
VERIDEX_INFERENCE_BATCH_SIZE=16
VERIDEX_MAX_DOCUMENT_CHARACTERS=500000
```

`model_source` values: `registry` (default), `local`, `mock`.

To run against the published Hub weights without a local MLflow database:

```bash
huggingface-cli download Bartu0nder/Veridex-QA-cuad-deberta-v3 --local-dir outputs/veridex-qa/best-model
```

```powershell
$env:VERIDEX_MODEL_SOURCE="local"
$env:VERIDEX_LOCAL_MODEL_PATH="outputs/veridex-qa/best-model"
```

## Run the API

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Interactive docs: `http://127.0.0.1:8000/docs`

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

```bash
curl http://127.0.0.1:8000/health
```

A healthy process reports `model_status: loaded` and `model_source: Veridex-QA@staging` (or the local path you configured). `model_load_error` stays `null` when weights loaded.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Process health, loaded model, threshold, and load error if any |
| `GET` | `/clause-categories` | Catalog names, risk levels, and CUAD-style questions |
| `POST` | `/analyze` | Extract clauses from `document_text` and return spans plus a risk summary |

`POST /analyze` body:

```json
{
  "document_name": "supply_agreement.txt",
  "document_text": "This Agreement shall automatically renew...",
  "contract_type": "supply",
  "clause_categories": ["Governing Law", "Cap On Liability"]
}
```

`clause_categories` is optional. Omit it to scan the full catalog. Names accept CUAD title case (`Governing Law`) or slugs (`governing_law`). `contract_type` is one of `lease`, `supply`, `nda`, `service`, `employment`, `other`.

Response includes `findings` (span, offsets, confidence, risk), `risk_summary`, `categories_without_findings`, and `is_mock_response`. Documents over 500,000 characters return `413`.

## Training and evaluation

```bash
python -m training.train --config training/config.yaml
python -m training.evaluate --model-path outputs/veridex-qa/best-model --split test
python -m training.evaluate --model-path outputs/veridex-qa/best-model --split test --sweep-null-thresholds 0 -1 -2 -5
python -m training.registry --model-path outputs/veridex-qa/best-model
```

MLflow UI (after a local run):

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

Hyperparameters live in `training/config.yaml`: 4 epochs, lr `3e-5`, batch 16, `max_seq_length` 384, `doc_stride` 128, AdamW, weight decay 0.01, warmup ratio 0.1.

## License and data

Model weights follow the CUAD license (**CC BY 4.0**). Cite The Atticus Project when you use the dataset or the published checkpoint.
