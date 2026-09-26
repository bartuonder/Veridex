from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub.errors import LocalTokenNotFoundError

from training.config import resolve_path

MODEL_CARD_SOURCE = Path(__file__).resolve().parent / "model_card.md"
EXCLUDED_FILENAMES = frozenset(
    {
        "training_args.bin",
        "optimizer.pt",
        "scheduler.pt",
        "rng_state.pth",
        "trainer_state.json",
        "validation_metrics.json",
    }
)
REPO_ID_PLACEHOLDER = "REPLACE_WITH_REPO_ID"


def assemble_upload_directory(
    model_directory: Path,
    reports_directory: Path | None,
    repo_id: str,
    staging_directory: Path,
) -> Path:
    staging_directory.mkdir(parents=True, exist_ok=True)

    for source_file in sorted(model_directory.iterdir()):
        if source_file.is_file() and source_file.name not in EXCLUDED_FILENAMES:
            shutil.copy2(source_file, staging_directory / source_file.name)

    model_card = MODEL_CARD_SOURCE.read_text(encoding="utf-8").replace(REPO_ID_PLACEHOLDER, repo_id)
    (staging_directory / "README.md").write_text(model_card, encoding="utf-8")

    if reports_directory and reports_directory.is_dir():
        evaluation_directory = staging_directory / "evaluation"
        evaluation_directory.mkdir(exist_ok=True)
        for report_file in sorted(reports_directory.glob("*.json")):
            shutil.copy2(report_file, evaluation_directory / report_file.name)

    return staging_directory


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the Veridex clause extraction model to the Hugging Face Hub")
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--model-path", default="outputs/veridex-qa/best-model")
    parser.add_argument("--reports-dir", default="outputs/veridex-qa/reports")
    parser.add_argument("--staging-dir", default="outputs/hub-upload")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    model_directory = resolve_path(arguments.model_path)
    if not (model_directory / "config.json").exists():
        raise FileNotFoundError(f"No model found at {model_directory}")

    staging_directory = resolve_path(arguments.staging_dir)
    if staging_directory.exists():
        shutil.rmtree(staging_directory)

    assemble_upload_directory(
        model_directory,
        resolve_path(arguments.reports_dir),
        arguments.repo_id,
        staging_directory,
    )

    uploaded_files = sorted(
        str(path.relative_to(staging_directory)) for path in staging_directory.rglob("*") if path.is_file()
    )
    total_megabytes = sum(path.stat().st_size for path in staging_directory.rglob("*") if path.is_file()) / 1e6
    print(f"prepared {len(uploaded_files)} files ({total_megabytes:.1f} MB) in {staging_directory}")
    for filename in uploaded_files:
        print(f"  {filename}")

    if arguments.dry_run:
        print("\ndry run complete, nothing uploaded")
        return

    api = HfApi()
    try:
        account = api.whoami()
    except LocalTokenNotFoundError as error:
        raise SystemExit(
            "No Hugging Face token found. Run 'huggingface-cli login' or set HF_TOKEN, then retry."
        ) from error

    print(f"\nauthenticated as {account['name']}")
    api.create_repo(repo_id=arguments.repo_id, repo_type="model", private=arguments.private, exist_ok=True)
    api.upload_folder(
        folder_path=str(staging_directory),
        repo_id=arguments.repo_id,
        repo_type="model",
        commit_message="Add Veridex-QA contract clause extraction model fine-tuned on CUAD",
    )
    print(f"published https://huggingface.co/{arguments.repo_id}")


if __name__ == "__main__":
    main()
