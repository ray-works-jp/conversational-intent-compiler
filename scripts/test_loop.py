"""Contract tests for scripts/cic_loop.py (no model calls: backends are Python callables)."""
import hashlib, json, os, sqlite3, subprocess, sys, tempfile, unittest, warnings
from unittest import mock
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
        self.assertEqual((rounds, reason), (2, "suspended"))

    def test_t0_question_audit_failure_and_backend_error_never_end_the_loop(self):
        raw = "Reactかも。いい感じに"
        comp = scripted_compiler({
            "質問される入力": "どちらの環境ですか？ 1) Web 2) モバイル",
            raw: [IR_OK.format(raw=raw, q="作り話"), IR_OK.format(raw=raw, q="作り話")],  # fails the audit twice
        })
        def broken(prompt):
            raise RuntimeError("backend down")
        rounds, reason, text = self.run_loop(["こんにちは", "質問される入力", raw, "最後"], comp)
        self.assertEqual((rounds, reason), (4, "suspended"))
        self.assertIn("原文をそのまま渡します", text)
        rounds, reason, text = self.run_loop(["a", "b"], broken, broken)
        self.assertEqual((rounds, reason), (2, "suspended"))

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
        ais = [e["raw"] for e in evs if e["attrs"].get("agent_role") == "responder"]
        self.assertEqual(humans, raws + [":stop"])
        self.assertEqual(len(ais), 2)
        self.assertTrue(all(a.startswith("応答:") for a in ais))

    def test_complete_history_keeps_distant_reference_and_answer_tail(self):
        seen = []
        answer = "前置き" * 400 + "\n1番: A\n2番: 長期参照の対象\n" + "末尾の条件"
        def compiler(prompt):
            seen.append(prompt)
            return "【T0】"
        history = []
        L.run_round("最初の候補を出して", compiler, lambda p: answer, history, spec=SPEC, log=lambda p: None)
        for i in range(10):
            L.run_round(f"別の話題{i}", compiler, lambda p: "別の応答", history, spec=SPEC, log=lambda p: None)
        L.run_round("前の2番で", compiler, lambda p: "選択", history, spec=SPEC, log=lambda p: None)
        self.assertIn(answer, seen[-1])
        self.assertIn("最初の候補を出して", seen[-1])
        self.assertIn('"omitted_turns": 0', seen[-1])

    def test_explicit_history_limit_marks_omissions_without_truncating_included_text(self):
        history = [{"raw": "古い条件", "compiled": "", "answer": "old"},
                   {"raw": "最新", "compiled": "AI提案" * 700, "answer": "回答" * 700}]
        text = L.history_text(history, 1)
        self.assertIn('"omitted_turns": 1', text)
        self.assertIn("既知欠落", text)
        self.assertNotIn("古い条件", text)
        self.assertIn("AI提案" * 700, text)
        self.assertIn("回答" * 700, text)
        self.assertEqual(L.history_coverage(history, 0)["included_turns"], 2)
        with self.assertRaises(ValueError): L.history_text(history, -1)

    def test_question_and_answer_are_preserved_when_ledger_reopens(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "loop.db"
            first = L.LedgerSink(db, "resume")
            long_question = "候補: " + "質問原文" * 200 + "\n2番: 再開時にも必要な対象"
            self.run_loop(["曖昧な依頼"], lambda p: long_question, ledger=first)
            resumed = L.LedgerSink(db, "resume")
            self.assertEqual(resumed.n, 1)
            self.assertEqual(resumed.c, 1)
            self.assertEqual(resumed.restore_history()[0]["answer"], long_question)
            seen = []
            self.run_loop(["その2番で", ":stop"], lambda p: seen.append(p) or "【T0】", ledger=resumed)
            self.assertIn(long_question, seen[0])
            reloaded = L.LedgerSink(db, "resume")
            self.assertEqual(reloaded.n, 3)
            self.assertEqual(reloaded.a, 1)
            events = reloaded.events
            self.assertEqual(len({e["event_id"] for e in events}), len(events))
            questions = [e for e in events if e["attrs"].get("compiler_kind") == "question"]
            self.assertEqual(questions[0]["origin"], "assistant")
            self.assertTrue(questions[0]["attrs"]["visible_to_human"])
            self.assertEqual([e["raw"] for e in events if e["kind"] == "human"], ["曖昧な依頼", "その2番で", ":stop"])

    def test_restart_continues_legacy_human_and_responder_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "loop.db"
            first = L.LedgerSink(db, "resume")
            h = first.human("legacy raw")
            first.assistant("legacy answer", h)
            second = L.LedgerSink(db, "resume")
            self.assertEqual(second.human("new raw"), "resume:main:H2")
            self.assertEqual(second.assistant("new answer", "resume:main:H2"), "resume:main:A2")
            restored = L.LedgerSink(db, "resume").restore_history()
            self.assertEqual([(r["raw"], r["answer"]) for r in restored], [("legacy raw", "legacy answer"), ("new raw", "new answer")])

    def test_stop_is_user_control_and_ai_quoted_stop_never_stops(self):
        self.assertFalse(L.is_stop('":stop"'))
        self.assertFalse(L.is_stop("```\n:stop\n```"))
        self.assertFalse(L.is_stop("説明文の中の :stop"))
        rounds, reason, _ = self.run_loop(["相談", "次の相談", ":stop"], lambda p: "【T0】", lambda p: ":stop")
        self.assertEqual((rounds, reason), (2, "explicit_stop"))

    def test_eof_suspends_and_does_not_fabricate_a_user_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = L.LedgerSink(Path(temp) / "loop.db", "suspend")
            rounds, reason, log = self.run_loop(["継続予定"], lambda p: "【T0】", ledger=ledger)
            self.assertEqual((rounds, reason), (1, "suspended"))
            self.assertIn("入力待ち", log)
            events = L.LedgerSink(ledger.db, "suspend").events
            self.assertEqual([e["raw"] for e in events if e["origin"] == "user"], ["継続予定"])
            waiting = [e for e in events if e["attrs"].get("status") == "waiting"]
            self.assertEqual(waiting[-1]["attrs"]["lifecycle"], "suspended")
            self.assertEqual(waiting[-1]["origin"], "tool")

    def test_backend_failures_are_runtime_observations_not_assistant_answers(self):
        def broken(prompt):
            raise L.BackendError("process failed", returncode=7, stdout="false success text", stderr="full failure detail")
        with tempfile.TemporaryDirectory() as temp:
            ledger = L.LedgerSink(Path(temp) / "loop.db", "fail")
            self.run_loop(["依頼", ":stop"], broken, broken, ledger=ledger)
            saved = L.LedgerSink(ledger.db, "fail")
            failures = [e for e in saved.events if e["attrs"].get("status") == "failed"]
            self.assertEqual({e["attrs"]["stage"] for e in failures}, {"compiler", "responder"})
            self.assertTrue(all(e["origin"] == "tool" and e["kind"] == "action_status" for e in failures))
            self.assertTrue(all(e["attrs"]["stdout"] == "false success text" for e in failures))
            self.assertFalse(any(e["attrs"].get("agent_role") == "responder" for e in saved.events))
            row = saved.restore_history()[0]
            self.assertEqual(row["visible_origin"], "tool")
            self.assertIn("応答AIの呼び出しに失敗", row["answer"])

    def test_log_stores_stop_and_empty_human_raw_and_no_delta_is_applied(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "loop.jsonl"
            self.run_loop(["", "内容", ":stop"], lambda p: "【T0】", log_path=log)
            rows = [json.loads(line) for line in log.read_text("utf-8").splitlines()]
            self.assertEqual([r["raw"] for r in rows], ["", "内容", ":stop"])
            self.assertTrue(all(r["delta_applied"] is False for r in rows))
            self.assertTrue(all(r["authority_changed"] is False for r in rows))

    def test_hidden_ab_failure_does_not_replace_the_visible_response_on_resume(self):
        calls = []
        def responder(prompt):
            calls.append(prompt)
            if len(calls) == 2: raise RuntimeError("hidden AB failure")
            return "visible answer"
        with tempfile.TemporaryDirectory() as temp:
            ledger = L.LedgerSink(Path(temp) / "loop.db", "ab")
            self.run_loop(["human"], lambda p: "【T0】", responder, ledger=ledger, ab=True)
            history = L.LedgerSink(ledger.db, "ab").restore_history()
            self.assertEqual(history[0]["answer"], "visible answer")
            self.assertEqual(history[0]["visible_origin"], "assistant")
            self.assertIn("hidden AB failure", history[0]["failures"][-1]["message"])

    def test_missing_legacy_compiler_output_is_reported_as_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = L.LedgerSink(Path(temp) / "loop.db", "legacy")
            parent = ledger.human("legacy input")
            ledger.assistant("saved answer", parent)
            history = L.LedgerSink(ledger.db, "legacy").restore_history()
            coverage = L.history_coverage(history)
            self.assertEqual(coverage["omitted_turns"], 0)
            self.assertTrue(coverage["known_omissions"])
            self.assertIn("記録がない", L.history_text(history))


class BackendContracts(unittest.TestCase):
    def test_nonzero_exit_is_failure_even_with_success_like_stdout(self):
        completed = subprocess.CompletedProcess(["fake"], 3, "success-looking output\n", "failure detail")
        with mock.patch.object(L.subprocess, "run", return_value=completed) as runner:
            with self.assertRaises(L.BackendError) as caught: L._run(["fake"], "prompt")
        self.assertEqual(caught.exception.returncode, 3)
        self.assertEqual(caught.exception.stdout, "success-looking output\n")
        self.assertFalse(runner.call_args.kwargs["shell"])

    def test_success_output_is_not_stripped_and_empty_output_fails(self):
        completed = subprocess.CompletedProcess(["fake"], 0, "\n  exact answer\r\n", "")
        with mock.patch.object(L.subprocess, "run", return_value=completed): self.assertEqual(L._run(["fake"], "p"), completed.stdout)
        completed.stdout = "  \n"
        with mock.patch.object(L.subprocess, "run", return_value=completed):
            with self.assertRaises(L.BackendError): L._run(["fake"], "p")

    def test_claude_uses_explicit_tool_skill_hook_and_mcp_restrictions(self):
        with mock.patch.object(L, "_run", return_value="response") as runner:
            self.assertEqual(L.make_backend("claude")("prompt"), "response")
        argv, stdin = runner.call_args.args
        self.assertEqual(stdin, "prompt")
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        for flag in ["--disable-slash-commands", "--strict-mcp-config", "--safe-mode", "--no-chrome"]: self.assertIn(flag, argv)
        self.assertEqual(json.loads(argv[argv.index("--mcp-config") + 1]), {"mcpServers": {}})
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_agy_and_custom_commands_require_explicit_opt_in(self):
        for backend in ["agy", 'cmd:"C:\\Program Files\\Python\\python.exe" -c "print(1)"']:
            with self.assertRaises(ValueError): L.make_backend(backend)
            with warnings.catch_warnings(record=True) as messages:
                warnings.simplefilter("always")
                with mock.patch.object(L, "_run", return_value="reply"):
                    L.make_backend(backend, allow_agent_tools=True)("prompt")
                self.assertTrue(messages)

    def test_json_argv_preserves_spaces_quotes_empty_arguments_and_backslashes(self):
        argv = [r"C:\Program Files\Python\python.exe", "-c", 'print("quoted value")', "", r"C:\data\file.txt"]
        self.assertEqual(L.split_command(json.dumps(argv)), argv)
        with self.assertRaises(ValueError): L.split_command("[]")

    @unittest.skipUnless(os.name == "nt", "Windows native argv parser")
    def test_windows_quoted_command_uses_native_argv_rules(self):
        argv = [r"C:\Program Files\Python\python.exe", "-c", 'print("quoted value")', "", r"C:\data\file.txt"]
        self.assertEqual(L.split_command(subprocess.list2cmdline(argv)), argv)


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
