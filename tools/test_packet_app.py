"""Local HTTP API integration with disposable progress; never uses user data."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get
import server


class PacketAppTests(unittest.TestCase):
    def test_both_dialects_grading_guesses_progress_review_and_drafts(self):
        with tempfile.TemporaryDirectory(prefix="pafta_packet_app_") as folder:
            with patch.dict(os.environ, {"PAFTA_DATA": folder}):
                app, httpd = server.start(0, token="packet-test-local-only")
                base = f"http://127.0.0.1:{app.port}"
                def api(path, body=None):
                    data = json.dumps(body).encode() if body is not None else None
                    req = Request(base + path, data=data, headers={
                        "X-Pafta-Token": "packet-test-local-only", "Content-Type": "application/json"})
                    with urlopen(req, timeout=50) as response:
                        return json.load(response)
                try:
                    outline = api("/api/track/packets")["track"]
                    self.assertEqual(len(outline["ranks"]), 6)
                    self.assertEqual([l["id"] for m in outline["modules"] for l in m["lessons"]],
                                     [f"pk{i:02}" for i in range(1, 30)])
                    self.assertTrue(all(not l.get("missing") for m in outline["modules"] for l in m["lessons"]))
                    for dialect, code, expected in [("wireshark", "udp.port == 53", [3, 4, 14]),
                                                     ("bpf", "tcp dst port 443", [10, 12, 13, 15])]:
                        result = api("/api/run", {"track": "packets", "code": code,
                            "stdin": json.dumps({"dil": dialect, "kayit": "temel"})})
                        self.assertEqual(result["status"], "ok", result)
                        self.assertEqual(result["packet_ids"], expected)
                        self.assertEqual(len(result["packet_inventory"]["satirlar"]), 24)
                    lib = Library()
                    for lid in ("pk03", "pk13", "pk24", "pk29"):
                        lesson = lib.lesson("packets", lid)
                        public = api("/api/lesson/packets/" + lid)
                        self.assertTrue(all("solution" not in s and "test" not in s for s in public["lesson"]["steps"]))
                        guess_i, guess = next((i, s) for i, s in enumerate(lesson["steps"]) if s["kind"] == "tahmin")
                        real = get("packets").run(guess["code"], guess["stdin"])
                        output = "".join(text for kind, text in real["segs"] if kind == "out")
                        self.assertTrue(api("/api/guess", {"track": "packets", "lesson": lid,
                                            "step": guess_i, "guess": output})["correct"])
                        task_i, task = next((i, s) for i, s in enumerate(lesson["steps"]) if s["kind"] == "gorev")
                        request = {"track": "packets", "lesson": lid, "step": task_i}
                        self.assertNotEqual(api("/api/check", dict(request, code=task["starter"]))["status"], "pass")
                        result = api("/api/check", dict(request, code=task["solution"], stdin='{"dil":"wrong"}'))
                        self.assertEqual(result["status"], "pass", result)
                        progress = api("/api/lesson/packets/" + lid)["progress"]
                        self.assertTrue(progress["steps"][str(task_i)]["done"])
                        self.assertTrue(progress["steps"][str(guess_i)]["guess_ok"])
                    self.assertEqual(sum(api("/api/review")["kutular"]), 4)
                    cli_result = api('/api/run', {'track':'packets',
                        'code':'tshark -r secili -2 -o tcp.reassemble_out_of_order:TRUE -q --export-objects http,sonuc',
                        'stdin':json.dumps({'dil':'tshark','kayit':'tcp-sirasiz'})})
                    self.assertEqual(cli_result['status'],'ok',cli_result)
                    self.assertEqual(cli_result['exports'][0]['text'],'PAFTA-TCP-LAB')
                    self.assertTrue(cli_result['tablolar'])
                    capture_result = api('/api/run', {'track':'packets',
                        'code':'tcpdump -i lo -nn -s 64 -c 3 -w sonuc.pcap udp',
                        'stdin':json.dumps({'dil':'tcpdump-lab','laboratuvar':'kisa'})})
                    self.assertEqual(capture_result['status'],'ok',capture_result)
                    self.assertEqual(capture_result['exports'][0]['caplens'],[63,64,64])
                    self.assertTrue(capture_result['runtime']['reaped'])
                    api("/api/draft", {"dil": "packets", "playground": "tcp dst port 443"})
                    self.assertEqual(api("/api/playground?dil=packets")["code"], "tcp dst port 443")
                    disk = json.loads(Path(folder, "progress.json").read_text(encoding="utf-8"))
                    self.assertIn("packets", disk["tracks"])
                finally:
                    httpd.shutdown()
                    httpd.server_close()


if __name__ == "__main__":
    unittest.main()
