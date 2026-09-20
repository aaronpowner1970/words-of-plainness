"""Session 14, phase 6 (CODE-SJN-19), phase 1: ONE minimal metered call, to prove the harness key works
before any track is started.

The key is read by the harness's own api_executor.load_key(--key-file) and is never printed, logged or
copied. On failure only the EXCEPTION CLASS and the HTTP status are reported -- never the message body,
which can echo credential material.

  python data-sources/sjn/recovery-runs/session14/key_probe.py --key-file <path>
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sjn_recovery.config import MODEL_IDS  # noqa: E402
from sjn_recovery.llm import LIST_PRICES   # noqa: E402

spec = importlib.util.spec_from_file_location("apix", os.path.join(ROOT, "scripts", "sjn_recovery", "api_executor.py"))
apix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apix)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--model", default="sonnet")
    a = ap.parse_args()

    model_id = MODEL_IDS.get(a.model, a.model)
    key = apix.load_key(a.key_file)          # the harness's own reader; the value never leaves this frame
    import anthropic
    client = anthropic.Anthropic(api_key=key, max_retries=0, timeout=60.0)
    out = {"what": "phase 1 key probe: one minimal metered call", "key_file": a.key_file,
           "backend": "anthropic", "model_id": model_id}
    try:
        r = client.messages.create(model=model_id, max_tokens=4, messages=[{"role": "user", "content": "ping"}])
        usage = {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
        out.update(ok=True, usage=usage, cost_usd=apix.cost_of(model_id, usage),
                   cost_basis="metered input/output tokens at list prices",
                   stop_reason=getattr(r, "stop_reason", None))
    except Exception as e:                    # class and status only -- never str(e)
        out.update(ok=False, error_class=type(e).__name__, http_status=getattr(e, "status_code", None))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    with open(os.path.join(HERE, "phase6-key-probe.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
