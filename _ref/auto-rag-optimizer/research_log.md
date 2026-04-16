# Auto-RAG-Optimizer Research Log

This file tracks every experiment run by the autonomous optimizer.
The table below is machine-readable — each row is one experiment.

## Results

| experiment_id | chunk_size | chunk_overlap | top_k | embedding_model | llm_model | temperature | search_type | splitter | faithfulness | answer_relevance | avg_score | tokens | cost | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 256 | 20 | 5 | qwen/qwen3-embedding-8b | nvidia/nemotron-3-nano-30b-a3b:free | 0.0 | similarity | recursive | 0.64 | 0.09 | 0.365 | 65876 | $0.0000 | baseline |
| 1 | 512 | 40 | 8 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity | recursive | 0.9 | 0.375 | 0.6375 | 95607 | $0.0020 | keep |
| 2 | 512 | 80 | 12 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity_score_threshold | recursive | 0.95 | 0.24 | 0.595 | 112026 | $0.0026 | discard |
| 3 | 512 | 60 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity | recursive | 0.0 | 0.0 | 0.0 | 0 | $0.0000 | crash |
| 4 | 512 | 80 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity | recursive | 1.0 | 0.245 | 0.6225 | 102714 | $0.0023 | discard |
| 5 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.2 | similarity | recursive | 0.85 | 0.355 | 0.6025 | 123401 | $0.0024 | discard |
| 6 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity_score_threshold | recursive | 0.9 | 0.335 | 0.6175 | 105539 | $0.0024 | discard |
| 7 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity_score_threshold | recursive | 0.9 | 0.35 | 0.625 | 107051 | $0.0024 | discard |
| 8 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-122b-a10b | 0.0 | similarity | recursive | 0.8 | 0.385 | 0.5925 | 127154 | $0.0109 | discard |
| 9 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.0 | similarity_score_threshold | recursive | 0.85 | 0.385 | 0.6175 | 107469 | $0.0024 | discard |
| 10 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | recursive | 0.9 | 0.4 | 0.65 | 103672 | $0.0024 | keep |
| 11 | 512 | 60 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity_score_threshold | recursive | 0.875 | 0.395 | 0.635 | 107034 | $0.0025 | discard |
| 12 | 512 | 40 | 12 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.05 | similarity | recursive | 0.8 | 0.44 | 0.62 | 141125 | $0.0028 | discard |
| 13 | 512 | 80 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | recursive | 0.955 | 0.25 | 0.6025 | 103630 | $0.0023 | discard |
| 14 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.05 | similarity | recursive | 0.9 | 0.34 | 0.62 | 78981 | $0.0024 | discard |
| 15 | 512 | 80 | 12 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.15 | similarity | recursive | 0.85 | 0.23 | 0.54 | 99234 | $0.0026 | discard |
| 16 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.05 | similarity | recursive | 0.9 | 0.37 | 0.635 | 106024 | $0.0024 | discard |
| 17 | 512 | 40 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | character | 0.85 | 0.59 | 0.72 | 626787 | $0.0204 | keep |
| 18 | 512 | 80 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | character | 0.9 | 0.605 | 0.7525 | 632850 | $0.0207 | keep |
| 19 | 512 | 100 | 12 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | character | 0.85 | 0.59 | 0.72 | 756210 | $0.0249 | discard |
| 20 | 512 | 90 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | character | 0.85 | 0.59 | 0.72 | 677129 | $0.0204 | discard |
| 21 | 512 | 90 | 10 | qwen/qwen3-embedding-8b | qwen/qwen3.5-flash-02-23 | 0.1 | similarity | character | 0.85 | 0.605 | 0.7275 | 624144 | $0.0203 | discard |
