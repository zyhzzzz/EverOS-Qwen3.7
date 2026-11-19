"""Loopback-only Qwen provider using the official Transformers inference recipes.

This serves model inference only; memory extraction and retrieval remain in EverOS.
"""
import os
import threading
from pathlib import Path
import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
import uvicorn

ROOT = Path(os.environ.get('EVEROS_MODELS_ROOT', '/home/REDACTED/openclaw-everos-assets'))
lock = threading.Lock()
app = FastAPI()
emb_name = 'Qwen/Qwen3-Embedding-4B'
rank_name = 'Qwen/Qwen3-Reranker-4B'
emb_tok = AutoTokenizer.from_pretrained(ROOT / 'Qwen3-Embedding-4B', padding_side='left')
emb = AutoModel.from_pretrained(ROOT / 'Qwen3-Embedding-4B', torch_dtype=torch.float16,
                               attn_implementation='sdpa').to(os.environ.get('EMBED_DEVICE', 'cuda:0')).eval()
rank_tok = AutoTokenizer.from_pretrained(ROOT / 'Qwen3-Reranker-4B', padding_side='left')
rank = AutoModelForCausalLM.from_pretrained(ROOT / 'Qwen3-Reranker-4B', torch_dtype=torch.float16,
                                          attn_implementation='sdpa').to(os.environ.get('RERANK_DEVICE', 'cuda:1')).eval()
prefix = rank_tok.encode('<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n', add_special_tokens=False)
suffix = rank_tok.encode('<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n', add_special_tokens=False)
yes, no = [rank_tok.convert_tokens_to_ids(t) for t in ('yes', 'no')]

@app.get('/health')
def health():
    return {'status': 'ok', 'models': [emb_name, rank_name]}

@app.post('/v1/embeddings')
def embeddings(body: dict):
    if body.get('model') != emb_name:
        raise HTTPException(400, 'Unknown embedding model')
    texts = body['input']
    texts = [texts] if isinstance(texts, str) else texts
    if not all(isinstance(t, str) for t in texts):
        raise HTTPException(400, 'Only text inputs supported')
    rows, tokens = [], 0
    with lock, torch.inference_mode():
        for i, text in enumerate(texts):
            batch = emb_tok(text, return_tensors='pt', truncation=True, max_length=32768).to(emb.device)
            tokens += int(batch['attention_mask'].sum())
            vector = emb(**batch).last_hidden_state[:, -1].float()
            dimensions = body.get('dimensions', vector.shape[-1])
            if not 32 <= dimensions <= vector.shape[-1]:
                raise HTTPException(400, 'Unsupported dimensions')
            vector = F.normalize(vector[:, :dimensions], dim=-1)
            rows.append({'object': 'embedding', 'index': i, 'embedding': vector[0].tolist()})
    return {'object': 'list', 'model': emb_name, 'data': rows,
            'usage': {'prompt_tokens': tokens, 'total_tokens': tokens}}

@app.post('/rerank')
def rerank(body: dict):
    if body.get('model') != rank_name:
        raise HTTPException(400, 'Unknown reranker model')
    results = []
    with lock, torch.inference_mode():
        for i, document in enumerate(body['documents']):
            text = document if isinstance(document, str) else document['text']
            pair = '<Instruct>: Given a web search query, retrieve relevant passages that answer the query\n<Query>: ' + body['query'] + '\n<Document>: ' + text
            ids = rank_tok.encode(pair, add_special_tokens=False, truncation=True,
                                  max_length=8192-len(prefix)-len(suffix))
            batch = rank_tok.pad({'input_ids': [prefix + ids + suffix]}, return_tensors='pt').to(rank.device)
            logits = rank(**batch, logits_to_keep=1).logits[0, -1, [no, yes]].float()
            score = float(torch.softmax(logits, dim=-1)[1])
            results.append({'index': i, 'relevance_score': score})
    results.sort(key=lambda r: r['relevance_score'], reverse=True)
    return {'results': results[:body.get('top_n', len(results))]}

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=19102, access_log=False)
