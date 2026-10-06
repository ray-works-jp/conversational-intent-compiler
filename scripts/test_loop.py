"""Contract tests for scripts/cic_loop.py (no model calls: backends are Python callables)."""
import hashlib, json, sqlite3, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cic_loop as L  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPEC = "SPEC"

IR_OK = '<ir tier="1"><raw>{raw}</raw><latitude on="x" q="{q}"/></ir>'


def scripted_compiler(table):
    """Compiler stub: picks a reply by the raw input found at the end of the prompt."""
    def f(prompt):
        for raw, reply in table.items():
            if prompt.rstrip().split("# 入力（対話モード）\n")[-1].split("\n# 前回")[0].strip() == raw:
                return reply.pop(0) if isinstance(reply, list) else reply
        return "【T0】そのまま渡して大丈夫です"
    return f


def echo_responder(prompt):
    return "応答: " + prompt.split("# 人間の入力（今回）\n")[-1].strip()


class LoopContinuesUntilExplicitStop(unittest.TestCase):
    def run_loop(self, inputs, compiler, responder=echo_responder, **kw):
        out = []
        rounds, reason = L.loop(compiler, responder, iter(inputs), spec=SPEC, log=out.append, **kw)
        return rounds, reason, "\n".join(out)

    def test_repeats_for_every_input_and_stops_only_on_explicit_stop(self):
        inputs = ["一つ目", "二つ目", "三つ目", ":stop", "これは処理されない"]
        rounds, reason, _ = self.run_loop(inputs, scripted_compiler({}))
        self.assertEqual((rounds, reason), (3, "explicit_stop"))

    def test_all_stop_words_stop_and_normal_requests_do_not(self):
        for w in L.STOP_WORDS:
            self.assertEqual(self.run_loop(["a", w, "b"], scripted_compiler({}))[:2], (1, "explicit_stop"), w)
        # a request that merely contains "止めて" is an ordinary input, not a stop
        rounds, reason, _ = self.run_loop(["サーバーを止めて", "もう一回"], scripted_compiler({}))
        self.assertEqual((rounds, reason), (2, "end_of_input"))

    def test_t0_question_audit_failure_and_backend_error_never_end_the_loop(self):
        raw = "Reactかも。いい感じに"
        comp = scripted_compiler({
            "質問される入力": "どちらの環境ですか？ 1) Web 2) モバイル",
            raw: [IR_OK.format(raw=raw, q="作り話"), IR_OK.format(raw=raw, q="作り話")],  # fails the audit twice
        })
        def broken(prompt):
            raise RuntimeError("backend down")
        rounds, reason, text = self.run_loop(["こんにちは", "質問される入力", raw, "最後"], comp)
        self.assertEqual((rounds, reason), (4, "end_of_input"))
        self.assertIn("原文をそのまま渡します", text)
        rounds, reason, text = self.run_loop(["a", "b"], broken, broken)
        self.assertEqual((rounds, reason), (2, "end_of_input"))

    def test_question_goes_to_the_human_and_skips_the_responder(self):
        calls = []
        def responder(p):
            calls.append(p)
            return "応答"
        comp = scripted_compiler({"曖昧": "どちらですか？"})
        self.run_loop(["曖昧"], comp, responder)
        self.assertEqual(calls, [])

    def test_ir_reaches_the_responder_only_after_passing_the_audit(self):
        raw = "いい感じにまとめて"
        seen = []
        def responder(p):
            seen.append(p)
            return "ok"
        good = scripted_compiler({raw: IR_OK.format(raw=raw, q="いい感じに")})
        self.run_loop([raw], good, responder)
        self.assertIn("解釈メモ（IR）", seen[-1])
        bad = scripted_compiler({raw: [IR_OK.format(raw=raw, q="ない語"), IR_OK.format(raw=raw, q="ない語")]})
        self.run_loop([raw], bad, responder)
        self.assertNotIn("解釈メモ（IR）", seen[-1])

    def test_history_is_passed_forward(self):
        prompts = []
        def comp(p):
            prompts.append(p)
            return "【T0】そのまま渡して大丈夫です"
        self.run_loop(["最初の入力", "二番目の入力"], comp)
        self.assertNotIn("最初の入力", prompts[0].split("# 履歴")[1].split("# 入力")[0])
        self.assertIn("最初の入力", prompts[1].split("# 履歴")[1].split("# 入力")[0])

    def test_ab_mode_records_the_passthrough_answer(self):
        raw = "いい感じにまとめて"
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "log.jsonl"
            comp = scripted_compiler({raw: IR_OK.format(raw=raw, q="いい感じに")})
            self.run_loop([raw], comp, ab=True, log_path=str(log))
            rec = json.loads(log.read_text("utf-8").splitlines()[0])
        self.assertTrue(rec["passed_ir"])
        self.assertIn("ab_passthrough_answer", rec)

    def test_ledger_captures_inputs_and_answers_verbatim(self):
        with tempfile.TemporaryDirectory() as t:
            db = Path(t) / "l.db"
            ledger = L.LedgerSink(db, "lp")
            raws = ["えっと、来週の  資料\n（改行も空白もそのまま）", "二つ目"]
            self.run_loop(raws + [":stop"], scripted_compiler({}), ledger=ledger)
            c = sqlite3.connect(db)
            evs = [json.loads(p) for (p,) in c.execute("select payload from events order by seq")]
            c.close()
        humans = [e["raw"] for e in evs if e["kind"] == "human"]
        ais = [e["raw"] for e in evs if e["kind"] == "assistant"]
        self.assertEqual(humans, raws)
        self.assertEqual(len(ais), 2)
        self.assertTrue(all(a.startswith("応答:") for a in ais))


class AuditTests(unittest.TestCase):
    RAW = "数字は去年のやつ使って。いい感じに"

    def test_good_ir_passes(self):
        ir = '<ir tier="2"><latitude on="見た目" q="いい感じに"/><constraint id="c1" src="u" q="数字は去年のやつ使って" strength="must"/></ir>'
        self.assertEqual(L.audit_ir(ir, self.RAW)[0], [])

    def test_failures(self):
        cases = {
            "q not verbatim": '<ir tier="1"><constraint src="u" q="数字を去年のやつで"/></ir>',
            "src=u without q": '<ir tier="1"><constraint src="u"/></ir>',
            "must from derived": '<ir tier="1"><constraint src="d" strength="must">x</constraint></ir>',
            "assume without if_wrong": '<ir tier="1"><basis><assume>x</assume></basis></ir>',
            "bad tier": '<ir tier="9"/>',
            "not xml": "<ir tier='1'>",
        }
        for name, ir in cases.items():
            self.assertTrue(L.audit_ir(ir, self.RAW)[0], name)

    def test_xml_tricks_are_refused_before_parsing(self):
        for ir in ('<!DOCTYPE ir [<!ENTITY a "aaaa">]><ir tier="1"><raw>&a;</raw></ir>',
                   '<ir tier="1"><![CDATA[x]]></ir>', '<?xml version="1.0"?><ir tier="1"/>',
                   '<ir tier="1">' + "x" * 25000 + "</ir>"):
            errors, _ = L.audit_ir(ir, self.RAW)
            self.assertTrue(errors)

    def test_invented_numbers_are_warned_not_rejected(self):
        ir = '<ir tier="1"><constraint src="d" strength="prefer">500語以内</constraint></ir>'
        errors, warnings = L.audit_ir(ir, self.RAW)
        self.assertEqual(errors, [])
        self.assertTrue(any("500" in w for w in warnings))

    def test_classify(self):
        self.assertEqual(L.classify("【T0】そのまま渡して大丈夫です")[0], "t0")
        self.assertEqual(L.classify('```xml\n<ir tier="1"/>\n```')[0], "ir")
        self.assertEqual(L.classify("どちらですか？")[0], "question")


class BundledFirstCompiler(unittest.TestCase):
    def test_first_compiler_files_are_unmodified(self):
        sums = (ROOT / "resources" / "intent-compiler" / "SHA256SUMS.txt").read_text("utf-8").splitlines()
        self.assertEqual(len(sums), 7)
        for line in sums:
            digest, name = line.split(" *", 1)
            self.assertEqual(hashlib.sha256((ROOT / "resources" / "intent-compiler" / name).read_bytes()).hexdigest(), digest, name)

    def test_loop_uses_the_bundled_spec(self):
        self.assertTrue(L.SPEC.exists())
        self.assertIn("Intent Compiler 実行仕様", L.SPEC.read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
