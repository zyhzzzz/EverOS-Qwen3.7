"""Install the historical answer-selection patch with synthetic regression checks."""
from pathlib import Path
import hashlib, json, difflib

r=Path(__file__).resolve().parent
path=r/'benchmark/src/agents/openclaw/openclaw.py'
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='cc50b709ae3a6027b25bc32fa2ead49ea9c16015cd2ae2a060aa0863edfe4aca'
src=raw.decode()
helper='''
def _final_public_answer(records):
    last = None
    for record in records:
        msg = record.get("message", {})
        if msg.get("role") == "assistant":
            last = msg
    if not last or last.get("stopReason") != "stop":
        return ""
    return "\\n".join(block["text"] for block in last.get("content", [])
                     if isinstance(block, dict) and block.get("type") == "text"
                     and block.get("text", "").strip()).strip()

'''
ns={}
exec(helper,ns)
pick=ns['_final_public_answer']
assert pick([{'message':{'role':'assistant','stopReason':'stop','content':[{'type':'text','text':'answer'}]}}]) == 'answer'
assert not pick([{'message':{'role':'assistant','stopReason':'toolUse','content':[{'type':'text','text':'interim'}]}}])
assert not pick([{'message':{'role':'assistant','stopReason':'stop','content':[{'type':'thinking','thinking':'private'}]}}])
start=src.index('        if not d.get("response"):',src.index('    def call_agent('))
end=src.index('        return d',start)
src=src[:start]+'''        d["upstream_cli_response"] = d.get("response", "")
        path = self._session_file(session_id)
        with path.open(encoding="utf-8") as stream:
            d["response"] = _final_public_answer(json.loads(line) for line in stream if line.strip())
        d["response_source"] = "final_public_stop" if d["response"] else "no_public_final"
'''+src[end:]
src=src.replace('class OpenClawAdapter(',helper+'class OpenClawAdapter(')
compile(src,str(path),'exec')
(r/'answer-selection.diff').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True),src.splitlines(True),fromfile='upstream',tofile='reviewed')))
path.write_text(src, encoding='utf-8', newline='\n')
print('Synthetic answer-selection checks passed. Adapter SHA256:',hashlib.sha256(path.read_bytes()).hexdigest())
