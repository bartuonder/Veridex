from __future__ import annotations

import random
from functools import partial
from typing import Any

from datasets import Dataset, DatasetDict, load_dataset
from transformers import PreTrainedTokenizerBase

CONTEXT_SEQUENCE_ID = 1


def load_cuad_splits(dataset_config: dict[str, Any], seed: int) -> DatasetDict:
    raw = _load_raw_dataset(dataset_config)
    train_split, validation_split = _split_by_contract(
        raw["train"], dataset_config["validation_contract_ratio"], seed
    )
    train_split = _limit_examples(train_split, dataset_config.get("max_train_examples"), seed)
    validation_split = _limit_examples(validation_split, dataset_config.get("max_eval_examples"), seed)
    return DatasetDict(
        train=train_split,
        validation=validation_split,
        test=raw["test"],
    )


def _load_raw_dataset(dataset_config: dict[str, Any]) -> DatasetDict:
    candidates: list[tuple[str, str | None]] = [
        (dataset_config["name"], dataset_config.get("revision")),
        (dataset_config["name"], None),
    ]
    candidates += [(name, None) for name in dataset_config.get("fallback_names") or []]

    failures: list[str] = []
    for name, revision in candidates:
        try:
            dataset = load_dataset(name, revision=revision, cache_dir=dataset_config["cache_dir"])
        except Exception as error:
            failures.append(f"{name}@{revision or 'main'}: {type(error).__name__}: {error}")
            continue
        return _normalise_splits(dataset, seed=0)

    raise RuntimeError("Could not load any CUAD dataset variant:\n" + "\n".join(failures))


def _normalise_splits(dataset: DatasetDict, seed: int) -> DatasetDict:
    required_columns = {"id", "title", "context", "question", "answers"}
    missing = required_columns - set(next(iter(dataset.values())).column_names)
    if missing:
        raise ValueError(f"Dataset is missing expected SQuAD columns: {sorted(missing)}")
    if "test" in dataset:
        return DatasetDict(train=dataset["train"], test=dataset["test"])
    if "validation" in dataset:
        return DatasetDict(train=dataset["train"], test=dataset["validation"])
    train_split, test_split = _split_by_contract(dataset["train"], 0.2, seed)
    return DatasetDict(train=train_split, test=test_split)


def _split_by_contract(dataset: Dataset, holdout_ratio: float, seed: int) -> tuple[Dataset, Dataset]:
    titles = sorted(set(dataset["title"]))
    generator = random.Random(seed)
    generator.shuffle(titles)
    holdout_size = max(1, round(len(titles) * holdout_ratio))
    holdout_titles = set(titles[:holdout_size])
    keep_titles = set(titles[holdout_size:])
    kept = dataset.filter(lambda example: example["title"] in keep_titles, desc="Selecting train contracts")
    holdout = dataset.filter(lambda example: example["title"] in holdout_titles, desc="Selecting holdout contracts")
    return kept, holdout


def _limit_examples(dataset: Dataset, limit: int | None, seed: int) -> Dataset:
    if not limit or len(dataset) <= limit:
        return dataset
    return dataset.shuffle(seed=seed).select(range(limit)).flatten_indices()


def build_train_features(
    dataset: Dataset,
    tokenizer: PreTrainedTokenizerBase,
    model_config: dict[str, Any],
    preprocessing_config: dict[str, Any],
    seed: int,
) -> Dataset:
    mapper = partial(
        _prepare_train_features,
        tokenizer=tokenizer,
        max_seq_length=model_config["max_seq_length"],
        doc_stride=model_config["doc_stride"],
        negative_windows_per_example=preprocessing_config["negative_windows_per_example"],
        seed=seed,
    )
    return dataset.map(
        mapper,
        batched=True,
        batch_size=preprocessing_config["map_batch_size"],
        num_proc=preprocessing_config.get("num_proc") or None,
        remove_columns=dataset.column_names,
        desc="Tokenizing training windows",
    )


def build_eval_features(
    dataset: Dataset,
    tokenizer: PreTrainedTokenizerBase,
    model_config: dict[str, Any],
    preprocessing_config: dict[str, Any],
) -> Dataset:
    mapper = partial(
        _prepare_eval_features,
        tokenizer=tokenizer,
        max_seq_length=model_config["max_seq_length"],
        doc_stride=model_config["doc_stride"],
    )
    return dataset.map(
        mapper,
        batched=True,
        batch_size=preprocessing_config["map_batch_size"],
        num_proc=preprocessing_config.get("num_proc") or None,
        remove_columns=dataset.column_names,
        desc="Tokenizing evaluation windows",
    )


def _tokenize_windows(
    examples: dict[str, list[Any]],
    tokenizer: PreTrainedTokenizerBase,
    max_seq_length: int,
    doc_stride: int,
):
    questions = [question.lstrip() for question in examples["question"]]
    return tokenizer(
        questions,
        examples["context"],
        truncation="only_second",
        max_length=max_seq_length,
        stride=doc_stride,
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        padding="max_length",
    )


def _prepare_train_features(
    examples: dict[str, list[Any]],
    tokenizer: PreTrainedTokenizerBase,
    max_seq_length: int,
    doc_stride: int,
    negative_windows_per_example: int | None,
    seed: int,
) -> dict[str, list[Any]]:
    encodings = _tokenize_windows(examples, tokenizer, max_seq_length, doc_stride)
    sample_mapping = encodings["overflow_to_sample_mapping"]
    offset_mapping = encodings["offset_mapping"]

    start_positions: list[int] = []
    end_positions: list[int] = []
    holds_answer: list[bool] = []

    for feature_index, offsets in enumerate(offset_mapping):
        input_ids = encodings["input_ids"][feature_index]
        cls_index = input_ids.index(tokenizer.cls_token_id)
        sequence_ids = encodings.sequence_ids(feature_index)
        answers = examples["answers"][sample_mapping[feature_index]]

        span = _locate_answer_span(answers, offsets, sequence_ids)
        if span is None:
            start_positions.append(cls_index)
            end_positions.append(cls_index)
            holds_answer.append(False)
        else:
            start_positions.append(span[0])
            end_positions.append(span[1])
            holds_answer.append(True)

    kept_indices = _select_feature_indices(
        sample_mapping,
        holds_answer,
        negative_windows_per_example,
        examples["id"],
        seed,
    )

    features: dict[str, list[Any]] = {
        "input_ids": [encodings["input_ids"][index] for index in kept_indices],
        "attention_mask": [encodings["attention_mask"][index] for index in kept_indices],
        "start_positions": [start_positions[index] for index in kept_indices],
        "end_positions": [end_positions[index] for index in kept_indices],
    }
    if "token_type_ids" in encodings:
        features["token_type_ids"] = [encodings["token_type_ids"][index] for index in kept_indices]
    return features


def _locate_answer_span(
    answers: dict[str, list[Any]],
    offsets: list[tuple[int, int]],
    sequence_ids: list[int | None],
) -> tuple[int, int] | None:
    if not answers["answer_start"]:
        return None

    start_char = answers["answer_start"][0]
    end_char = start_char + len(answers["text"][0])

    context_start = 0
    while context_start < len(sequence_ids) and sequence_ids[context_start] != CONTEXT_SEQUENCE_ID:
        context_start += 1
    if context_start == len(sequence_ids):
        return None
    context_end = len(sequence_ids) - 1
    while sequence_ids[context_end] != CONTEXT_SEQUENCE_ID:
        context_end -= 1

    if offsets[context_start][0] > start_char or offsets[context_end][1] < end_char:
        return None

    token_start = context_start
    while token_start <= context_end and offsets[token_start][1] <= start_char:
        token_start += 1
    token_end = context_end
    while token_end >= context_start and offsets[token_end][0] >= end_char:
        token_end -= 1
    if token_start > token_end:
        return None
    return token_start, token_end


def _select_feature_indices(
    sample_mapping: list[int],
    holds_answer: list[bool],
    negative_windows_per_example: int | None,
    example_ids: list[str],
    seed: int,
) -> list[int]:
    if negative_windows_per_example is None:
        return list(range(len(sample_mapping)))

    kept: list[int] = []
    negatives_by_sample: dict[int, list[int]] = {}
    for feature_index, is_positive in enumerate(holds_answer):
        if is_positive:
            kept.append(feature_index)
        else:
            negatives_by_sample.setdefault(sample_mapping[feature_index], []).append(feature_index)

    for sample_index, negative_indices in negatives_by_sample.items():
        if len(negative_indices) > negative_windows_per_example:
            generator = random.Random(f"{seed}:{example_ids[sample_index]}")
            negative_indices = generator.sample(negative_indices, negative_windows_per_example)
        kept.extend(negative_indices)

    return sorted(kept)


def _prepare_eval_features(
    examples: dict[str, list[Any]],
    tokenizer: PreTrainedTokenizerBase,
    max_seq_length: int,
    doc_stride: int,
) -> dict[str, list[Any]]:
    encodings = _tokenize_windows(examples, tokenizer, max_seq_length, doc_stride)
    sample_mapping = encodings["overflow_to_sample_mapping"]

    example_ids: list[str] = []
    context_offsets: list[list[tuple[int, int] | None]] = []

    for feature_index in range(len(encodings["input_ids"])):
        sequence_ids = encodings.sequence_ids(feature_index)
        example_ids.append(examples["id"][sample_mapping[feature_index]])
        context_offsets.append(
            [
                offset if sequence_ids[token_index] == CONTEXT_SEQUENCE_ID else None
                for token_index, offset in enumerate(encodings["offset_mapping"][feature_index])
            ]
        )

    features: dict[str, list[Any]] = {
        "input_ids": encodings["input_ids"],
        "attention_mask": encodings["attention_mask"],
        "example_id": example_ids,
        "offset_mapping": context_offsets,
    }
    if "token_type_ids" in encodings:
        features["token_type_ids"] = encodings["token_type_ids"]
    return features
