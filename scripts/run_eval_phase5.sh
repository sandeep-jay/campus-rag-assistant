#!/usr/bin/env bash
# Run RAGAS eval with tuned Phase 5 retrieval (from repo root).
set -euo pipefail
cd "$(dirname "$0")/.."
export RAG_ENGINE=langgraph
export RERANK_ENABLED=true
export RERANK_BACKEND=keyword
export RERANK_TOP_N=3
export RERANK_CANDIDATE_K=10
export RERANK_PREFILTER_MAX=10
export RERANK_MIN_KEYWORD_OVERLAP=0
export MULTI_QUERY_ENABLED=true
export MULTI_QUERY_COUNT=2
export METADATA_FILTER_ENABLED=false
export METADATA_FILTER_CLIENT_ENABLED=false
echo "Phase 5 eval (tuned): keyword rerank + 2 extra queries + RRF + prefilter"
tox -e eval
