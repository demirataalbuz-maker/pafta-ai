"""Native packet curriculum audit, including numeric and Boolean mutations.

--audit-json PATH saves all observed results for an independent reviewer.
Mutants which pass are reported, never silently counted as killed. A surviving
equivalent expression can be documented in EQUIVALENT only after review.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get


# (lesson, zero-based step, original expression, mutated expression): reason.
EQUIVALENT = {
    ("pk14", 3, "ip[0] & 0x0f > 5", "ip[0] & 14 > 5"):
        "For every byte, (byte & 15)>5 iff (byte & 14)>5: both select low-nibble values 6..15.",
}
assert all(((byte & 15) > 5) == ((byte & 14) > 5) for byte in range(256))


def boolean_alias(original, changed):
    # Documented native semantics, not an exception inferred from our corpus:
    # wireshark-filter(4): Boolean true is ANY non-zero integer. Thus 1→2
    # cannot be killed by adding packets. False↔true mutants remain required.
    pattern = r"\b(?:tcp\.flags\.(?:syn|ack|reset|fin)|dns\.flags\.response)\s*(?:==|!=)\s*(\d+)\b"
    for match in re.finditer(pattern, original):
        old = int(match[1])
        for new in (old - 1, old + 1):
            candidate = original[:match.start(1)] + str(new) + original[match.end(1):]
            if old > 0 and new > 0 and candidate == changed:
                return "Wireshark Boolean: all non-zero literals mean true (wireshark-filter(4))"
    return None


def mutations(code, dialect="wireshark"):
    seen = {code}
    def changed(start, end, value, label):
        mutated = code[:start] + value + code[end:]
        if mutated not in seen:
            seen.add(mutated)
            return label, mutated
    for m in re.finditer(r">=|<=|==|!=|&&|\|\||(?<![<>=!])[<>=](?!=)|!(?!=)|\b(?:and|or|not|true|false)\b|(?<!&)&(?!&)", code):
        old = m[0]
        target = {">=": ">", "<=": "<", ">": ">=", "<": "<=", "==": "!=", "!=": "==",
                  "=": "!=", "and": "or", "or": "and", "not": "", "&": "|",
                  "&&": "||", "||": "&&", "!": "", "true": "false", "false": "true"}[old]
        item = changed(m.start(), m.end(), target, f"{old}→{target} at {m.start()}")
        if item:
            yield item
    # Numeric operands (ports, masks, lengths, CIDR widths); IP/MAC octets and
    # field names are not changed. Every numeric boundary gets both neighbours.
    for m in re.finditer(r"(?<![\w.:])(?:0x[0-9a-fA-F]+|\d+)(?![\w.:])", code):
        value = int(m[0], 16 if m[0].startswith("0x") else 10)
        for delta in (-1, 1):
            target = value + delta
            if target < 0:
                continue
            item = changed(m.start(), m.end(), str(target), f"{m[0]}→{target} at {m.start()}")
            if item:
                yield item
    if dialect == "bpf":
        for match in re.finditer(r"\[(\d+)(?::(\d+))?\]", code):
            for group in (1, 2):
                if match[group] is None:
                    continue
                value = int(match[group])
                for delta in (-1, 1):
                    target = value + delta
                    if target < 0:
                        continue
                    item = changed(match.start(group), match.end(group), str(target),
                                   f"byte accessor {value}→{target} at {match.start(group)}")
                    if item:
                        yield item
    fields = {"ip": "ip6" if dialect == "bpf" else "ipv6", "ip6": "ip", "ipv6": "ip", "tcp": "udp", "udp": "tcp", "arp": "ip",
              "src": "dst", "dst": "src", "tcp-syn": "tcp-ack", "tcp-ack": "tcp-syn",
              "ip.src": "ip.dst", "ip.dst": "ip.src", "ip.addr": "ip.src",
              "ipv6.src": "ipv6.dst", "ipv6.dst": "ipv6.src", "ipv6.addr": "ipv6.src",
              "tcp.srcport": "tcp.dstport", "tcp.dstport": "tcp.srcport", "tcp.port": "tcp.dstport",
              "udp.srcport": "udp.dstport", "udp.dstport": "udp.srcport", "udp.port": "udp.dstport",
              "frame.len": "frame.cap_len", "frame.cap_len": "frame.len",
              "tcp.flags.syn": "tcp.flags.ack", "tcp.flags.ack": "tcp.flags.syn"}
    for m in re.finditer(r"\b[A-Za-z_][\w.-]*\b", code):
        if m[0] in fields:
            item = changed(m.start(), m.end(), fields[m[0]], f"{m[0]}→{fields[m[0]]} at {m.start()}")
            if item:
                yield item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-json")
    parser.add_argument("--progress-jsonl", help="Tamamlanmamış denetimde de ölçülen işleri satır satır kaydet")
    parser.add_argument("--lessons", nargs="*")
    args = parser.parse_args()
    library = Library()
    track = library.track("packets")
    ranks = track.get("ranks", [])
    ids = [lid for module in track["modules"] for lid in module["lessons"]]
    assert len(ranks) == 6 and len({r["id"] for r in ranks}) == 6
    assert ids == [f"pk{i:02}" for i in range(1, 30)], ids
    assert all(module.get("lessons") for module in track["modules"])
    records, failures, tasks, predictions = [], [], 0, 0
    jobs = []
    for lid in ids:
        if args.lessons and lid not in args.lessons:
            continue
        lesson = library.lesson("packets", lid)
        if lesson is None:
            failures.append(f"{lid}: missing lesson")
            continue
        guesses = [s for s in lesson["steps"] if s["kind"] == "tahmin"]
        if not guesses:
            failures.append(f"{lid}: missing prediction")
        for index, step in enumerate(lesson["steps"]):
            try:
                config = json.loads(step.get("stdin", "{}"))
                if config.get("dil") != step.get("meta", {}).get("dil"):
                    failures.append(f"{lid}:{index}: meta.dil differs from stdin.dil")
            except ValueError:
                failures.append(f"{lid}:{index}: invalid input JSON")
            if step["kind"] == "tahmin":
                predictions += 1
                result = get("packets").run(step["code"], step.get("stdin", ""))
                output = "".join(t for kind, t in result.get("segs", []) if kind == "out").strip()
                if result["status"] != "ok" or not output or output not in step["body"].split("???")[-1]:
                    failures.append(f"{lid}:{index}: native prediction differs: {output} {result.get('error')}")
                if step.get("gercek") is not None:
                    failures.append(f"{lid}:{index}: fixed prediction is forbidden")
            if step["kind"] == "gorev":
                tasks += 1
                jobs.append((lid, index, step, "solution", step["solution"]))
                jobs.append((lid, index, step, "starter", step.get("starter", "")))
                for label, code in mutations(step["solution"], json.loads(step["stdin"])["dil"]):
                    jobs.append((lid, index, step, label, code))

    def execute(job):
        lid, index, step, label, code = job
        result = get("packets").test(code, step)
        return {"lesson": lid, "step": index, "change": label, "code": code,
                "status": result["status"], "error": result.get("error"),
                "failed_checks": [c for c in result.get("checks", []) if not c["ok"]][:2]}
    progress = Path(args.progress_jsonl).open("w", encoding="utf-8") if args.progress_jsonl else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for row in pool.map(execute, jobs):
            records.append(row)
            if progress:
                progress.write(json.dumps(row, ensure_ascii=False) + "\n")
                progress.flush()
                if len(records) % 50 == 0:
                    print(f"ölçülen {len(records)}/{len(jobs)}", flush=True)
            original = library.lesson("packets", row["lesson"])["steps"][row["step"]].get("solution")
            key = (row["lesson"], row["step"], original, row["code"])
            equivalent = EQUIVALENT.get(key) or boolean_alias(original, row["code"])
            if equivalent and row["status"] == "pass":
                row["equivalent"] = equivalent
            if row["change"] == "solution":
                bad = row["status"] != "pass"
            else:
                bad = row["status"] in ("pass", "internal", "timeout") and not row.get("equivalent")
            if bad:
                failures.append(f"{row['lesson']}:{row['step']} {row['change']}: {row['status']} | {row['code']} | {row['error']} {row['failed_checks']}")
    if progress:
        progress.close()
    summary = {"lessons": len(set(r["lesson"] for r in records)), "tasks": tasks, "predictions": predictions,
               "mutations": len(records) - 2 * tasks, "equivalent": sum("equivalent" in r for r in records),
               "failures": failures, "records": records}
    if args.audit_json:
        Path(args.audit_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"{summary['lessons']} ders / {tasks} görev / {predictions} tahmin / {summary['mutations']} mutasyon")
    for failure in failures:
        print(failure)
    print("TEMİZ" if not failures else f"{len(failures)} bulgu")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
