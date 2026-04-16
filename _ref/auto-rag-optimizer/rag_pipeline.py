"""
RAG Pipeline module for Auto-RAG-Optimizer.
Loads parameters from config.json, indexes documents from docs/ folder,
and answers questions from test_questions.jsonl.
"""

import json
import os
import glob
import hashlib
import logging
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.callbacks.manager import get_openai_callback

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
CONFIG_PATH = BASE_DIR / "config.json"
QUESTIONS_PATH = BASE_DIR / "test_questions.jsonl"
RESULTS_PATH = BASE_DIR / "results.json"
INDEX_DIR = BASE_DIR / ".faiss_index"


def load_config() -> dict[str, Any]:
    """Load the current RAG configuration."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_documents(docs_dir: Path | None = None) -> list:
    """Load all supported documents from the docs/ folder."""
    docs_dir = docs_dir or DOCS_DIR
    documents = []

    loaders_map = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
    }

    for ext, loader_cls in loaders_map.items():
        for filepath in glob.glob(str(docs_dir / f"**/*{ext}"), recursive=True):
            try:
                loader = loader_cls(filepath)
                documents.extend(loader.load())
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")

    if not documents:
        raise FileNotFoundError(
            f"No documents found in {docs_dir}. "
            "Place .pdf, .txt, or .md files in the docs/ folder."
        )

    logger.info(f"Loaded {len(documents)} document chunks from {docs_dir}")
    return documents


def get_text_splitter(config: dict) -> RecursiveCharacterTextSplitter | CharacterTextSplitter:
    """Return a text splitter based on config."""
    splitter_type = config.get("splitter", "recursive")
    chunk_size = config.get("chunk_size", 512)
    chunk_overlap = config.get("chunk_overlap", 50)

    if splitter_type == "character":
        return CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    else:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# --- Token usage tracking ---
_token_usage = {"embedding_tokens": 0, "llm_prompt_tokens": 0, "llm_completion_tokens": 0}


def reset_token_usage():
    """Reset token counters for a new experiment."""
    global _token_usage
    _token_usage = {"embedding_tokens": 0, "llm_prompt_tokens": 0, "llm_completion_tokens": 0}


def get_token_usage() -> dict:
    """Return current token usage counts."""
    return dict(_token_usage)


def get_embeddings(config: dict) -> OpenAIEmbeddings:
    """Return the embedding model via OpenRouter."""
    return OpenAIEmbeddings(
        model=config.get("embedding_model", "qwen/qwen3-embedding-8b"),
        openai_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        openai_api_base=OPENROUTER_BASE_URL,
    )


def compute_index_cache_key(config: dict) -> str:
    """Compute a cache key from parameters that affect the FAISS index."""
    key_parts = {
        "chunk_size": config.get("chunk_size", 512),
        "chunk_overlap": config.get("chunk_overlap", 50),
        "splitter": config.get("splitter", "recursive"),
        "embedding_model": config.get("embedding_model", "qwen/qwen3-embedding-8b"),
    }
    key_str = json.dumps(key_parts, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()[:12]


def build_vectorstore(documents: list, config: dict) -> FAISS:
    """Split documents and build a FAISS vector store, with caching."""
    cache_key = compute_index_cache_key(config)
    cache_dir = INDEX_DIR / cache_key
    cache_meta = cache_dir / "cache_meta.json"
    embeddings = get_embeddings(config)

    # Check if a cached index exists for this parameter combination
    if cache_dir.exists() and cache_meta.exists():
        try:
            vectorstore = FAISS.load_local(
                str(cache_dir), embeddings, allow_dangerous_deserialization=True
            )
            logger.info(
                f"Loaded cached FAISS index (key={cache_key}) — "
                f"skipping re-embedding (chunk_size={config.get('chunk_size')}, "
                f"model={config.get('embedding_model')})"
            )
            return vectorstore
        except Exception as e:
            logger.warning(f"Cache load failed (key={cache_key}): {e}. Rebuilding...")

    # No cache hit — split, embed, and save
    splitter = get_text_splitter(config)
    splits = splitter.split_documents(documents)
    logger.info(
        f"Split into {len(splits)} chunks "
        f"(chunk_size={config.get('chunk_size')}, overlap={config.get('chunk_overlap')})"
    )

    vectorstore = FAISS.from_documents(splits, embeddings)

    cache_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(cache_dir))
    with open(cache_meta, "w") as f:
        json.dump({
            "chunk_size": config.get("chunk_size"),
            "chunk_overlap": config.get("chunk_overlap"),
            "splitter": config.get("splitter"),
            "embedding_model": config.get("embedding_model"),
            "num_chunks": len(splits),
        }, f, indent=2)
    logger.info(f"FAISS index built and cached (key={cache_key})")

    return vectorstore


def get_retriever(vectorstore: FAISS, config: dict):
    """Create a retriever from the vector store with config parameters."""
    search_type = config.get("search_type", "similarity")
    top_k = config.get("top_k", 3)

    search_kwargs = {"k": top_k}

    if search_type == "similarity_score_threshold" and config.get("score_threshold"):
        search_kwargs["score_threshold"] = config["score_threshold"]
        return vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs,
        )

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )


def build_rag_chain(retriever, config: dict):
    """Build a langchain RAG chain."""
    llm = ChatOpenAI(
        model=config.get("llm_model", "qwen/qwen3.5-flash-02-23"),
        temperature=config.get("temperature", 0.0),
        openai_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        openai_api_base=OPENROUTER_BASE_URL,
        model_kwargs={"extra_body": {"reasoning": {"effort": "none"}}},
        request_timeout=60.0,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Use ONLY the context below to answer. If the context does not contain the answer, "
            "say 'I cannot find the answer in the provided documents.'\n\n"
            "Context:\n{context}"
        )),
        ("human", "{question}"),
    ])

    def format_docs(docs):
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain, retriever


def load_questions() -> list[dict]:
    """Load test questions from JSONL file."""
    questions = []
    with open(QUESTIONS_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    if not questions:
        raise FileNotFoundError(f"No questions found in {QUESTIONS_PATH}")
    logger.info(f"Loaded {len(questions)} test questions")
    return questions


def run_pipeline(config: dict | None = None) -> dict:
    """
    Execute the full RAG pipeline:
    1. Load config
    2. Load and index documents
    3. Answer all test questions
    4. Save results to results.json

    Returns a dict with questions, answers, and contexts.
    """
    if config is None:
        config = load_config()

    logger.info(f"Running RAG pipeline with config: {json.dumps(config, indent=2)}")

    reset_token_usage()

    # Load and index
    documents = load_documents()
    vectorstore = build_vectorstore(documents, config)
    retriever = get_retriever(vectorstore, config)
    chain, retriever = build_rag_chain(retriever, config)

    # Answer questions
    questions_data = load_questions()
    results = {
        "questions": [],
        "answers": [],
        "contexts": [],
        "ground_truths": [],
    }

    with get_openai_callback() as cb:
        for item in questions_data:
            question = item["question"]
            ground_truth = item.get("ground_truth", "")

            try:
                answer = chain.invoke(question)
                retrieved_docs = retriever.invoke(question)
                contexts = [doc.page_content for doc in retrieved_docs]
            except Exception as e:
                logger.error(f"Error answering '{question}': {e}")
                answer = f"Error: {e}"
                contexts = []

            results["questions"].append(question)
            results["answers"].append(answer)
            results["contexts"].append(contexts)
            results["ground_truths"].append(ground_truth)

        _token_usage["llm_prompt_tokens"] += cb.prompt_tokens
        _token_usage["llm_completion_tokens"] += cb.completion_tokens
        _token_usage["embedding_tokens"] += cb.total_tokens - cb.prompt_tokens - cb.completion_tokens

    logger.info(
        f"Pipeline token usage — prompt: {cb.prompt_tokens}, "
        f"completion: {cb.completion_tokens}, total: {cb.total_tokens}"
    )

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Pipeline complete. Results saved to {RESULTS_PATH}")
    return results


# --- Cost estimation ---
MODEL_COSTS = {
    # per 1M tokens: (input, output)
    "qwen/qwen3.5-flash-02-23": (0.07, 0.28),
    "qwen/qwen3.5-122b-a10b": (0.26, 2.08),
    "nvidia/nemotron-3-nano-30b-a3b:free": (0.0, 0.0),
    "qwen/qwen3-embedding-8b": (0.02, 0.0),
}


def estimate_cost(token_usage: dict, config: dict) -> dict:
    """Estimate cost in USD based on token usage and model."""
    llm_model = config.get("llm_model", "qwen/qwen3.5-flash-02-23")
    emb_model = config.get("embedding_model", "text-embedding-3-small")

    llm_input_rate, llm_output_rate = MODEL_COSTS.get(llm_model, (0.07, 0.28))
    emb_input_rate, _ = MODEL_COSTS.get(emb_model, (0.02, 0.0))

    llm_input_cost = token_usage.get("llm_prompt_tokens", 0) / 1_000_000 * llm_input_rate
    llm_output_cost = token_usage.get("llm_completion_tokens", 0) / 1_000_000 * llm_output_rate
    emb_cost = token_usage.get("embedding_tokens", 0) / 1_000_000 * emb_input_rate

    total = round(llm_input_cost + llm_output_cost + emb_cost, 6)
    return {
        "llm_input_cost": round(llm_input_cost, 6),
        "llm_output_cost": round(llm_output_cost, 6),
        "embedding_cost": round(emb_cost, 6),
        "total_cost_usd": total,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    config = load_config()
    results = run_pipeline(config)
    print(f"Answered {len(results['questions'])} questions.")
    for q, a in zip(results["questions"], results["answers"]):
        print(f"\nQ: {q}\nA: {a[:200]}...")
