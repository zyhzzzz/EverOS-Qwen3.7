"""Launch the upstream MCP server against the existing local corpus."""
import os
import logging
import faulthandler
import signal
from pathlib import Path
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
faulthandler.register(signal.SIGUSR1)

root = Path(__file__).resolve().parent
bench = root / 'EvoAgentBench-benchmark-6aa4990'
old = Path.home() / 'openclaw/evoagentbench-ir-repro'
sys.path.insert(0, str(bench / 'src/utils/browsecomp-plus-tools/searcher'))
os.environ.setdefault('HF_DATASETS_CACHE', '/home/REDACTED/openclaw-everos-assets/datasets-cache')
sys.argv = ['mcp_server', '--searcher-type', 'faiss', '--transport', 'sse',
            '--port', '19101', '--k', '5', '--snippet-max-tokens', '512',
            '--index-path', str(old / 'data/browsecomp-plus-indexes/qwen3-embedding-8b/corpus.*.pkl'),
            '--model-name', str(old / 'models/Qwen3-Embedding-8B'),
            '--dataset-name', str(old / 'data/browsecomp-plus-corpus')]
from mcp_server import main
main()
