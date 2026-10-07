import threading
import time
import unittest
from dataclasses import replace
from class_record_helper.core import Runner, Settings, parse_cells, plan_actions


class RecordingKeyboard:
    def __init__(self):
        self.events = []

    def type_text(self, value):
        self.events.append(("text", value))

    def press_key(self, value):
        self.events.append(("key", value))


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(initial_delay=0, key_delay_ms=0)

    def execute(self, text, **kwargs):
        settings = replace(self.settings, **kwargs)
        backend = RecordingKeyboard()
        actions = plan_actions(parse_cells(text), settings)
        result = Runner(backend).run(actions, settings)
        self.assertEqual(result, "Done")
        return backend.events

    def test_parse_cells(self):
        self.assertEqual(parse_cells(" 90\t\t José \r\n\t85\t\r\n\r\n"),
                         [["90", "", "José"], ["", "85", ""]])
        self.assertEqual(parse_cells("1\n\n2"), [["1"], [""], ["2"]])
        self.assertEqual(parse_cells("1\r2"), [["1"], ["2"]])

    def test_empty_input(self):
        for text in ("", " \n", "\t\r\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_cells(text)

    def test_each_single_advance_row_major_and_no_final_enter(self):
        for key in ("Enter", "Tab", "Down", "Right"):
            with self.subTest(key=key):
                self.assertEqual(self.execute("1\t2\n3\t4", advance=key),
                                 [(kind, value) for v in "1234"
                                  for kind, value in (("text", v), ("key", key))])

    def test_blanks_preserve_position(self):
        self.assertEqual(self.execute("1\t\t3"),
                         [("text", "1"), ("key", "Enter"), ("key", "Enter"),
                          ("text", "3"), ("key", "Enter")])
        self.assertEqual(self.execute("1\t", skip_blanks=False),
                         [("text", "1"), ("key", "Enter"), ("text", ""), ("key", "Enter")])

    def test_multi_column_counts(self):
        for columns in range(1, 6):
            matrix = [[f"{r}{c}" for c in range(5)] for r in range(3)]
            expected = []
            for c in range(columns):
                if c:
                    expected += [("key", "Right"), ("key", "Up"), ("key", "Up")]
                for r in range(3):
                    expected += [("text", matrix[r][c]), ("key", "Enter")]
            text = "\n".join("\t".join(row) for row in matrix)
            self.assertEqual(self.execute(text, multi_column=True, columns=columns), expected)

    def test_one_row_and_column_clamping(self):
        self.assertEqual(self.execute("1\t2", multi_column=True, columns=5),
                         [("text", "1"), ("key", "Enter"), ("key", "Right"),
                          ("text", "2"), ("key", "Enter")])

    def test_uneven_rows(self):
        self.assertEqual(self.execute("1\t2\n3", multi_column=True, columns=2),
                         [("text", "1"), ("key", "Enter"), ("text", "3"),
                          ("key", "Enter"), ("key", "Right"), ("key", "Up"),
                          ("text", "2"), ("key", "Enter"), ("key", "Enter")])

    def test_test_mode_never_calls_backend(self):
        for multi in (False, True):
            self.assertEqual(self.execute("1\t\n3\t4", multi_column=multi,
                                          columns=2, test_mode=True), [])

    def test_invalid_settings(self):
        for change in ({"initial_delay": -1}, {"key_delay_ms": -1},
                       {"initial_delay": float("nan")}, {"key_delay_ms": float("inf")},
                       {"columns": 6}, {"advance": "Left"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.settings, **change).validate()

    def test_stop_during_countdown(self):
        backend = RecordingKeyboard()
        runner = Runner(backend)
        settings = replace(self.settings, initial_delay=10)
        result = runner.run(plan_actions([["1"]], settings), settings,
                            countdown=lambda _: runner.stop())
        self.assertEqual(result, "Stopped")
        self.assertEqual(backend.events, [])

    def test_stop_during_delay_interrupts_wait(self):
        backend = RecordingKeyboard()
        runner = Runner(backend)
        settings = replace(self.settings, key_delay_ms=10000)
        reached = threading.Event()
        results = []
        thread = threading.Thread(target=lambda: results.append(runner.run(
            plan_actions([["1"], ["2"]], settings), settings,
            progress=lambda *_: reached.set())))
        thread.start()
        self.assertTrue(reached.wait(2))
        runner.stop()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, ["Stopped"])
        self.assertEqual(backend.events, [("text", "1")])

    def test_stop_between_columns_prevents_further_navigation(self):
        backend = RecordingKeyboard()
        runner = Runner(backend)
        settings = replace(self.settings, multi_column=True, columns=2)
        def progress(_, action):
            if action.value == "Right":
                runner.stop()
        result = runner.run(plan_actions([["1", "2"], ["3", "4"]], settings),
                            settings, progress)
        self.assertEqual(result, "Stopped")
        self.assertEqual(backend.events[-1], ("key", "Right"))
        self.assertNotIn(("key", "Up"), backend.events)

    def test_stop_before_start_and_after_final_action(self):
        for before in (True, False):
            runner = Runner(RecordingKeyboard())
            if before:
                runner.stop()
            actions = plan_actions([["1"]], self.settings)
            result = runner.run(actions, self.settings,
                                progress=lambda i, _: runner.stop() if i == len(actions) else None)
            self.assertEqual(result, "Stopped")


if __name__ == "__main__":
    unittest.main()
