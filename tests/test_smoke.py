import json
import os
import tempfile
import unittest
from unittest import mock

from agents.execution import execute
from agents.router import route_command
from agents.personality import BRUH_SYSTEM_PROMPT
from memory import memory as memory_store
from memory import context as context_mod
from voice import input as voice_input


# ---------------------------------------------------------------------------
# Router — original smoke tests
# ---------------------------------------------------------------------------

class RouterSmokeTest(unittest.TestCase):
    def test_fast_routing(self):
        self.assertEqual(route_command("search cats")[0], "search")
        self.assertEqual(route_command("open chrome")[0], "open_app")
        self.assertEqual(route_command("play lofi")[0], "play_media")

    def test_open_youtube_and_play_compound(self):
        intent, params = route_command("open youtube and play me a song")
        self.assertEqual(intent, "play_media_advanced")
        self.assertIn("query", params)
        self.assertTrue(len(params["query"]) > 0)

    def test_play_me_any_youtube_video_query(self):
        intent, params = route_command("play me any youtube video")
        self.assertEqual(intent, "play_media")
        self.assertEqual(params["query"], "youtube video")

    def test_play_that_youtube_video_for_me_query(self):
        intent, params = route_command("play that youtube video for me")
        self.assertEqual(intent, "play_media")
        self.assertEqual(params["query"], "that youtube video")

    def test_two_word_commands_route(self):
        self.assertEqual(route_command("open spotify")[0], "open_app")
        self.assertEqual(route_command("open whatsapp")[0], "open_app")
        self.assertEqual(route_command("close chrome")[0], "close_app")
        self.assertEqual(route_command("volume up")[0], "volume")


class RouterAliasTest(unittest.TestCase):
    def test_launch_alias(self):
        intent, params = route_command("launch spotify")
        self.assertEqual(intent, "open_app")
        self.assertEqual(params["app"], "spotify")

    def test_start_alias(self):
        intent, params = route_command("start notepad")
        self.assertEqual(intent, "open_app")
        self.assertEqual(params["app"], "notepad")

    def test_run_alias(self):
        intent, params = route_command("run chrome")
        self.assertEqual(intent, "open_app")
        self.assertEqual(params["app"], "chrome")

    def test_google_alias(self):
        intent, params = route_command("google python tutorials")
        self.assertEqual(intent, "search")
        self.assertEqual(params["query"], "python tutorials")

    def test_look_up_alias(self):
        intent, params = route_command("look up weather today")
        self.assertEqual(intent, "search")
        self.assertEqual(params["query"], "weather today")

    def test_find_alias(self):
        intent, params = route_command("find restaurants near me")
        self.assertEqual(intent, "search")
        self.assertEqual(params["query"], "restaurants near me")

    def test_find_me_alias(self):
        intent, params = route_command("find me a good recipe")
        self.assertEqual(intent, "search")
        self.assertEqual(params["query"], "a good recipe")

    def test_close_intent(self):
        intent, params = route_command("close chrome")
        self.assertEqual(intent, "close_app")
        self.assertEqual(params["app"], "chrome")

    def test_kill_alias(self):
        intent, params = route_command("kill notepad")
        self.assertEqual(intent, "close_app")
        self.assertEqual(params["app"], "notepad")

    def test_quit_alias(self):
        intent, params = route_command("quit spotify")
        self.assertEqual(intent, "close_app")
        self.assertEqual(params["app"], "spotify")

    def test_volume_up(self):
        intent, params = route_command("volume up")
        self.assertEqual(intent, "volume")
        self.assertEqual(params["action"], "up")

    def test_volume_down(self):
        intent, params = route_command("volume down")
        self.assertEqual(intent, "volume")
        self.assertEqual(params["action"], "down")

    def test_mute(self):
        intent, params = route_command("mute")
        self.assertEqual(intent, "volume")
        self.assertEqual(params["action"], "mute")

    def test_screenshot(self):
        intent, _ = route_command("screenshot")
        self.assertEqual(intent, "screenshot")


# ---------------------------------------------------------------------------
# Router — screen awareness keywords
# ---------------------------------------------------------------------------

class RouterScreenAwarenessTest(unittest.TestCase):
    def test_what_am_i_looking_at(self):
        intent, params = route_command("what am i looking at")
        self.assertEqual(intent, "analyze_context")
        self.assertIn("query", params)

    def test_whats_on_my_screen(self):
        intent, _ = route_command("what's on my screen right now")
        self.assertEqual(intent, "analyze_context")

    def test_the_code(self):
        intent, _ = route_command("what is this code on my screen")
        self.assertEqual(intent, "analyze_context")

    def test_read_my_screen(self):
        intent, _ = route_command("read my screen")
        self.assertEqual(intent, "analyze_context")

    def test_on_my_screen(self):
        intent, _ = route_command("explain what is on my screen")
        self.assertEqual(intent, "analyze_context")

    def test_what_app_is_open(self):
        intent, _ = route_command("what app is open right now")
        self.assertEqual(intent, "analyze_context")

    def test_see_my_screen(self):
        intent, _ = route_command("can you see my screen")
        self.assertEqual(intent, "analyze_context")

    def test_ui_tutor_phrase(self):
        intent, _ = route_command("what is this")
        self.assertEqual(intent, "ui_tutor")

    def test_ui_tutor_phrase_with_punctuation(self):
        intent, _ = route_command("what does this do?")
        self.assertEqual(intent, "ui_tutor")


# ---------------------------------------------------------------------------
# Router — Phase 3: web automation intents
# ---------------------------------------------------------------------------

class RouterWebAutomationTest(unittest.TestCase):
    def test_go_to(self):
        intent, params = route_command("go to google.com")
        self.assertEqual(intent, "navigate")
        self.assertEqual(params["url"], "google.com")

    def test_navigate_to(self):
        intent, params = route_command("navigate to github.com")
        self.assertEqual(intent, "navigate")
        self.assertEqual(params["url"], "github.com")

    def test_click(self):
        intent, params = route_command("click on submit button")
        self.assertEqual(intent, "web_click")
        self.assertEqual(params["target"], "submit button")

    def test_click_simple(self):
        intent, params = route_command("click login")
        self.assertEqual(intent, "web_click")
        self.assertEqual(params["target"], "login")

    def test_type(self):
        intent, params = route_command("type hello world")
        self.assertEqual(intent, "web_type")
        self.assertEqual(params["text"], "hello world")

    def test_scroll_down(self):
        intent, params = route_command("scroll down")
        self.assertEqual(intent, "web_scroll")
        self.assertEqual(params["direction"], "down")

    def test_scroll_up(self):
        intent, params = route_command("scroll up")
        self.assertEqual(intent, "web_scroll")
        self.assertEqual(params["direction"], "up")


# ---------------------------------------------------------------------------
# Router — create folder / file
# ---------------------------------------------------------------------------


class RouterFilesystemTest(unittest.TestCase):
    def test_create_folder_name_phrase(self):
        intent, params = route_command("create a folder name ghost")
        self.assertEqual(intent, "create_folder")
        self.assertEqual(params["name"], "ghost")

    def test_create_new_file_name_phrase(self):
        intent, params = route_command("create a new file name download")
        self.assertEqual(intent, "create_file")
        self.assertEqual(params["name"], "download")

    def test_make_folder_called(self):
        intent, params = route_command("make a folder called java stuff")
        self.assertEqual(intent, "create_folder")
        self.assertEqual(params["name"], "java stuff")

    def test_new_folder(self):
        intent, params = route_command("new folder backups")
        self.assertEqual(intent, "create_folder")
        self.assertEqual(params["name"], "backups")

    def test_new_file(self):
        intent, params = route_command("new file notes")
        self.assertEqual(intent, "create_file")
        self.assertEqual(params["name"], "notes")

    def test_create_folder_in_location(self):
        intent, params = route_command("create folder reports in desktop")
        self.assertEqual(intent, "create_folder")
        self.assertEqual(params["name"], "reports")
        self.assertEqual(params["parent"], "desktop")

    def test_copy_to(self):
        intent, params = route_command("copy ghost to desktop")
        self.assertEqual(intent, "fs_copy")
        self.assertEqual(params["src"], "ghost")
        self.assertEqual(params["dst"], "desktop")

    def test_move_to(self):
        intent, params = route_command("move ghost to downloads")
        self.assertEqual(intent, "fs_move")
        self.assertEqual(params["src"], "ghost")
        self.assertEqual(params["dst"], "downloads")

    def test_cut_to(self):
        intent, params = route_command("cut ghost to desktop")
        self.assertEqual(intent, "fs_move")

    def test_rename_to(self):
        intent, params = route_command("rename ghost to spook")
        self.assertEqual(intent, "fs_rename")
        self.assertEqual(params["src"], "ghost")
        self.assertEqual(params["dst"], "spook")

    def test_delete_path(self):
        intent, params = route_command("delete ghost")
        self.assertEqual(intent, "fs_delete")
        self.assertEqual(params["path"], "ghost")

    def test_delete_the_folder_phrase(self):
        intent, params = route_command("delete the folder ghost")
        self.assertEqual(intent, "fs_delete")
        self.assertEqual(params["path"], "the folder ghost")

    def test_remove_path(self):
        intent, params = route_command("remove ghost")
        self.assertEqual(intent, "fs_delete")

    def test_open_folder_not_open_app(self):
        intent, params = route_command("open folder desktop")
        self.assertEqual(intent, "fs_open")
        self.assertEqual(params["path"], "desktop")

    def test_open_file_intent(self):
        intent, params = route_command("open file notes.txt")
        self.assertEqual(intent, "fs_open")


# ---------------------------------------------------------------------------
# Execution — close / volume / screenshot
# ---------------------------------------------------------------------------

class CloseAppSmokeTest(unittest.TestCase):
    def test_close_app_execution(self):
        with mock.patch("agents.execution.close_app", return_value=True) as mock_close:
            result = execute("close_app", {"app": "notepad"})
            self.assertTrue(result)
            mock_close.assert_called_once_with("notepad")

    def test_close_app_failure(self):
        with mock.patch("agents.execution.close_app", return_value=False):
            result = execute("close_app", {"app": "nonexistent"})
            self.assertFalse(result)


class VolumeSmokeTest(unittest.TestCase):
    def test_volume_execution(self):
        with mock.patch("agents.execution.set_volume", return_value="Volume up") as mock_vol:
            result = execute("volume", {"action": "up"})
            self.assertEqual(result, "Volume up")
            mock_vol.assert_called_once_with("up")


class ScreenshotSmokeTest(unittest.TestCase):
    def test_screenshot_execution(self):
        with mock.patch("agents.execution.take_screenshot", return_value="/tmp/shot.png"):
            result = execute("screenshot", {})
            self.assertIn("shot.png", result)

    def test_screenshot_failure(self):
        with mock.patch("agents.execution.take_screenshot", return_value=None):
            result = execute("screenshot", {})
            self.assertIn("failed", result.lower())


# ---------------------------------------------------------------------------
# Execution — Phase 3: web automation intents
# ---------------------------------------------------------------------------

class WebAutomationExecutionTest(unittest.TestCase):
    def test_navigate_success(self):
        fake_page = mock.Mock()
        with mock.patch("agents.execution.navigate_to", return_value=fake_page):
            result = execute("navigate", {"url": "google.com"})
            self.assertEqual(result, "Navigated")

    def test_navigate_failure(self):
        with mock.patch("agents.execution.navigate_to", return_value=None):
            result = execute("navigate", {"url": "bad.url"})
            self.assertIn("Couldn't", result)

    def test_web_click_success(self):
        with mock.patch("agents.execution.click_element", return_value=True):
            result = execute("web_click", {"target": "login"})
            self.assertEqual(result, "Clicked")

    def test_web_click_failure(self):
        with mock.patch("agents.execution.click_element", return_value=False):
            result = execute("web_click", {"target": "missing"})
            self.assertIn("Couldn't", result)

    def test_web_type_success(self):
        with mock.patch("agents.execution.type_text", return_value=True):
            result = execute("web_type", {"text": "hello"})
            self.assertEqual(result, "Typed")

    def test_web_scroll_success(self):
        with mock.patch("agents.execution.scroll_page", return_value=True):
            result = execute("web_scroll", {"direction": "down"})
            self.assertEqual(result, "Scrolled down")

    def test_ui_tutor_execution(self):
        with mock.patch("agents.execution.handle_ui_tutor", return_value={"element": "menu"}):
            result = execute("ui_tutor", {"query": "what is this"})
            self.assertEqual(result["element"], "menu")


class ExecutionFilesystemTest(unittest.TestCase):
    def test_create_folder_delegates(self):
        with mock.patch(
            "agents.execution.fs_create_folder",
            return_value="Folder created at C:\\fake\\ghost",
        ):
            result = execute("create_folder", {"name": "ghost"})
            self.assertIn("Folder created", result)

    def test_create_file_delegates(self):
        with mock.patch(
            "agents.execution.fs_create_file",
            return_value="File created at C:\\fake\\a.txt",
        ):
            result = execute("create_file", {"name": "a"})
            self.assertIn("File created", result)

    def test_create_folder_empty_name(self):
        with mock.patch("agents.execution.fs_create_folder") as mock_cf:
            result = execute("create_folder", {"name": "   "})
            self.assertIn("Need a folder name", result)
            mock_cf.assert_not_called()

    def test_create_file_empty_name(self):
        with mock.patch("agents.execution.fs_create_file") as mock_f:
            result = execute("create_file", {"name": ""})
            self.assertIn("Need a file name", result)
            mock_f.assert_not_called()

    def test_fs_copy(self):
        with mock.patch("agents.execution.fs_copy", return_value="Copied to X"):
            result = execute("fs_copy", {"src": "a", "dst": "b"})
            self.assertEqual(result, "Copied to X")

    def test_fs_delete(self):
        with mock.patch("agents.execution.fs_delete", return_value="Deleted X"):
            result = execute("fs_delete", {"path": "ghost"})
            self.assertEqual(result, "Deleted X")


class FilesystemPathNormalizationTest(unittest.TestCase):
    def test_normalize_spoken_folder_prefix(self):
        from tools.filesystem_tools import _normalize_path_spec_text

        self.assertEqual(_normalize_path_spec_text("the folder ghost"), "ghost")
        self.assertEqual(_normalize_path_spec_text("folder reports"), "reports")


# ---------------------------------------------------------------------------
# Fast-path feedback
# ---------------------------------------------------------------------------

class FastPathFeedbackTest(unittest.TestCase):
    def _get_feedback(self):
        def _fast_path_feedback(intent, result):
            if intent == "open_app":
                return "Done" if result else "Couldn't open that"
            if intent == "close_app":
                return "Closed" if result else "Couldn't close that"
            if intent == "volume":
                return str(result) if result else None
            if intent == "screenshot":
                return "Screenshot saved" if result and "failed" not in str(result).lower() else "Screenshot failed"
            if intent == "remember":
                return "Got it"
            if intent == "recall":
                return str(result) if result else "I don't remember that"
            if intent == "analyze_context":
                return str(result)[:300] if result else None
            if intent in ("navigate", "web_click", "web_type", "web_scroll"):
                return str(result) if result else None
            if intent in (
                "create_folder",
                "create_file",
                "fs_copy",
                "fs_move",
                "fs_delete",
                "fs_rename",
                "fs_open",
            ):
                return str(result)[:300] if result else None
            return None
        return _fast_path_feedback

    def test_open_app_true(self):
        fb = self._get_feedback()
        self.assertEqual(fb("open_app", True), "Done")

    def test_open_app_false(self):
        fb = self._get_feedback()
        self.assertEqual(fb("open_app", False), "Couldn't open that")

    def test_close_app_true(self):
        fb = self._get_feedback()
        self.assertEqual(fb("close_app", True), "Closed")

    def test_volume_result(self):
        fb = self._get_feedback()
        self.assertEqual(fb("volume", "Volume up"), "Volume up")

    def test_screenshot_saved(self):
        fb = self._get_feedback()
        self.assertEqual(fb("screenshot", "Screenshot saved to /tmp/x.png"), "Screenshot saved")

    def test_recall_value(self):
        fb = self._get_feedback()
        self.assertEqual(fb("recall", "Blue"), "Blue")

    def test_recall_none(self):
        fb = self._get_feedback()
        self.assertEqual(fb("recall", None), "I don't remember that")

    def test_navigate_feedback(self):
        fb = self._get_feedback()
        self.assertEqual(fb("navigate", "Navigated"), "Navigated")

    def test_create_folder_feedback(self):
        fb = self._get_feedback()
        msg = "Folder created at C:\\Users\\x\\Documents\\BruhFiles\\ghost"
        self.assertEqual(fb("create_folder", msg), msg)

    def test_create_file_feedback_truncates(self):
        fb = self._get_feedback()
        long_msg = "File created at " + ("x" * 400)
        out = fb("create_file", long_msg)
        self.assertEqual(len(out), 300)

    def test_search_silent(self):
        fb = self._get_feedback()
        self.assertIsNone(fb("search", None))


# ---------------------------------------------------------------------------
# Personality
# ---------------------------------------------------------------------------

class PersonalitySmokeTest(unittest.TestCase):
    def test_bruh_prompt_is_not_empty(self):
        self.assertTrue(len(BRUH_SYSTEM_PROMPT) > 50)

    def test_bruh_prompt_has_personality_markers(self):
        lower = BRUH_SYSTEM_PROMPT.lower()
        self.assertIn("bruh", lower)
        self.assertIn("darkly funny", lower)

    def test_bruh_prompt_mentions_conversation_history(self):
        lower = BRUH_SYSTEM_PROMPT.lower()
        self.assertIn("conversation history", lower)

    def test_web_agent_uses_personality(self):
        import agents.web_agent as wa
        import inspect
        source = inspect.getsource(wa.run_web_agent)
        self.assertIn("bruh_prompt", source)

    def test_code_agent_uses_personality(self):
        import agents.code_agent as ca
        import inspect
        source = inspect.getsource(ca.run_code_agent)
        self.assertIn("bruh_prompt", source)

    def test_execution_uses_personality(self):
        import agents.execution as ex
        import inspect
        source = inspect.getsource(ex.execute)
        self.assertIn("bruh_prompt", source)


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------

class ContextFormattingTest(unittest.TestCase):
    def test_format_context_empty(self):
        orig = dict(context_mod.context)
        try:
            context_mod.context.update({
                "last_command": None, "last_response": None,
                "last_screen_text": None, "last_updated_at": None,
                "history": [],
            })
            result = context_mod.format_context()
            self.assertIn("No previous conversation", result)
        finally:
            context_mod.context.update(orig)

    def test_format_context_with_history(self):
        orig = dict(context_mod.context)
        try:
            context_mod.context.update({
                "last_command": None, "last_response": None,
                "last_screen_text": None, "last_updated_at": None,
                "history": [
                    {"command": "search cats", "response": None, "timestamp": "t1", "screen_text": None},
                    {"command": "what is that", "response": "It's a cat search", "timestamp": "t2", "screen_text": None},
                ],
            })
            result = context_mod.format_context()
            self.assertIn("User: search cats", result)
            self.assertIn("User: what is that", result)
            self.assertIn("Bruh: It's a cat search", result)
            self.assertIn("[Recent conversation]", result)
        finally:
            context_mod.context.update(orig)


# ---------------------------------------------------------------------------
# Planner screen heuristic
# ---------------------------------------------------------------------------

class PlannerScreenHeuristicTest(unittest.TestCase):
    def test_looking_at_routes_to_code_agent(self):
        from agents.planner import _looks_like_screen_question
        self.assertTrue(_looks_like_screen_question("what am i looking at"))
        self.assertTrue(_looks_like_screen_question("what is on my screen"))
        self.assertTrue(_looks_like_screen_question("read my screen"))
        self.assertTrue(_looks_like_screen_question("explain this code"))

    def test_normal_question_not_screen(self):
        from agents.planner import _looks_like_screen_question
        self.assertFalse(_looks_like_screen_question("what is python"))
        self.assertFalse(_looks_like_screen_question("tell me a joke"))


class UiTutorAgentSmokeTest(unittest.TestCase):
    def test_normalize_output_vscode(self):
        from agents.ui_tutor_agent import _normalize_output

        raw = json.dumps(
            {
                "element": "Explorer panel",
                "software": "VS Code",
                "explanation": "Shows project files.",
                "usage": "Use it to open files quickly.",
                "recommendation": "Use it now to jump to target file.",
                "confidence": "high",
            }
        )
        out = _normalize_output(raw)
        self.assertEqual(out["software"], "VS Code")
        self.assertEqual(out["confidence"], "high")

    def test_normalize_output_blender(self):
        from agents.ui_tutor_agent import _normalize_output

        raw = json.dumps(
            {
                "element": "Transform gizmo",
                "software": "Blender",
                "explanation": "Moves or rotates selected object.",
                "usage": "Drag axis handles to transform.",
                "recommendation": "Use it now for object alignment.",
                "confidence": "medium",
            }
        )
        out = _normalize_output(raw)
        self.assertEqual(out["software"], "Blender")
        self.assertEqual(out["confidence"], "medium")

    def test_normalize_output_browser(self):
        from agents.ui_tutor_agent import _normalize_output

        raw = json.dumps(
            {
                "element": "Address bar",
                "software": "Browser",
                "explanation": "Enter URLs or search terms.",
                "usage": "Type destination then press Enter.",
                "recommendation": "Use it now to navigate.",
                "confidence": "high",
            }
        )
        out = _normalize_output(raw)
        self.assertEqual(out["software"], "Browser")
        self.assertEqual(out["confidence"], "high")

    def test_build_speech_is_short(self):
        from agents.ui_tutor_agent import _build_speech

        out = _build_speech(
            {
                "element": "Insert menu",
                "explanation": "Use this to add elements quickly into your design canvas.",
            }
        )
        self.assertLessEqual(len(out), 120)


# ---------------------------------------------------------------------------
# Web agent real-time detection
# ---------------------------------------------------------------------------

class WebAgentRealtimeTest(unittest.TestCase):
    def test_weather_detected(self):
        from agents.web_agent import _needs_realtime
        self.assertTrue(_needs_realtime("what is the weather today"))
        self.assertTrue(_needs_realtime("what is the temperature"))

    def test_stock_detected(self):
        from agents.web_agent import _needs_realtime
        self.assertTrue(_needs_realtime("what is the stock price of apple"))

    def test_normal_question_not_realtime(self):
        from agents.web_agent import _needs_realtime
        self.assertFalse(_needs_realtime("what is python"))
        self.assertFalse(_needs_realtime("explain recursion"))


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

class FallbackSmokeTest(unittest.TestCase):
    def test_automation_failure_always_falls_back(self):
        with mock.patch("agents.execution.play_youtube_advanced", side_effect=RuntimeError("boom")), mock.patch(
            "agents.execution.play_youtube"
        ) as fallback:
            status = execute("play_media_advanced", {"query": "lofi beats"})
            self.assertEqual(status, "fallback")
            fallback.assert_called_once()


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class MemorySmokeTest(unittest.TestCase):
    def test_remember_and_recall_normalized(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = f"{tmp_dir}/memory.json"
            with mock.patch.object(memory_store, "MEMORY_FILE", tmp_file):
                previous = memory_store.remember("Favorite Color", "Blue")
                self.assertIsNone(previous)
                self.assertEqual(memory_store.recall("favorite color"), "Blue")
                self.assertEqual(memory_store.recall("fav color"), "Blue")


# ---------------------------------------------------------------------------
# Persistent context
# ---------------------------------------------------------------------------

class PersistentContextTest(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = f"{tmp_dir}/context.json"
            orig_file = context_mod.CONTEXT_FILE
            orig_context = dict(context_mod.context)
            try:
                context_mod.CONTEXT_FILE = tmp_file
                context_mod.context.update({
                    "last_command": None, "last_response": None,
                    "last_screen_text": None, "last_updated_at": None,
                    "history": [],
                })

                context_mod.update_context(command="test cmd", response="test resp")
                self.assertTrue(os.path.exists(tmp_file))

                with open(tmp_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.assertEqual(saved["last_command"], "test cmd")
                self.assertEqual(saved["last_response"], "test resp")
                self.assertEqual(len(saved["history"]), 1)
            finally:
                context_mod.CONTEXT_FILE = orig_file
                context_mod.context.update(orig_context)


class ContextHistoryBoundedTest(unittest.TestCase):
    def test_context_history_is_bounded(self):
        orig = dict(context_mod.context)
        try:
            context_mod.context.update({
                "last_command": None, "last_response": None,
                "last_screen_text": None, "last_updated_at": None,
                "history": [],
            })
            for index in range(15):
                context_mod.update_context(command=f"cmd-{index}", response=f"res-{index}")
            ctx = context_mod.get_context()
            self.assertEqual(len(ctx["history"]), 8)
            self.assertEqual(ctx["last_command"], "cmd-14")
        finally:
            context_mod.context.update(orig)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class ConfigTest(unittest.TestCase):
    def test_config_loads_defaults(self):
        import config
        self.assertIn("chrome", config.APP_MAP)
        self.assertIn("notepad", config.APP_MAP)
        self.assertTrue(len(config.TESSERACT_CMD) > 0)
        self.assertTrue(len(config.PLAYWRIGHT_USER_DATA_DIR) > 0)

    def test_config_has_process_map(self):
        import config
        self.assertIn("chrome", config.PROCESS_MAP)
        self.assertEqual(config.PROCESS_MAP["chrome"], "chrome.exe")

    def test_config_json_override(self):
        import config as config_mod_cfg
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = os.path.join(tmp_dir, "config.json")
            with open(cfg_path, "w") as f:
                json.dump({"tesseract_cmd": "/custom/tesseract"}, f)
            orig_overrides = config_mod_cfg._overrides
            try:
                with open(cfg_path, "r") as f:
                    config_mod_cfg._overrides = json.load(f)
                result = config_mod_cfg._get("tesseract_cmd", "default")
                self.assertEqual(result, "/custom/tesseract")
            finally:
                config_mod_cfg._overrides = orig_overrides


# ---------------------------------------------------------------------------
# Voice input
# ---------------------------------------------------------------------------

class VoiceInputSmokeTest(unittest.TestCase):
    def test_wait_timeout_returns_no_speech_status(self):
        recognizer = mock.Mock()
        recognizer.listen.side_effect = voice_input.sr.WaitTimeoutError()
        recognizer.adjust_for_ambient_noise.return_value = None
        recognizer.pause_threshold = 1.5
        recognizer.non_speaking_duration = 0.5
        recognizer.dynamic_energy_threshold = True

        mic_ctx = mock.Mock()
        mic_ctx.__enter__ = mock.Mock(return_value=mock.Mock())
        mic_ctx.__exit__ = mock.Mock(return_value=False)

        with mock.patch.object(voice_input, "_recognizer", recognizer), \
             mock.patch.object(voice_input, "_calibrated", True), \
             mock.patch.object(voice_input.sr, "Microphone", return_value=mic_ctx):
            result = voice_input.listen_command()
            self.assertEqual(result["status"], "no_speech")


# ---------------------------------------------------------------------------
# Fix 4: Single-word command whitelist
# ---------------------------------------------------------------------------

class SingleWordWhitelistTest(unittest.TestCase):
    """Verify the router handles bare single-word commands correctly."""

    def test_bare_stop_routes_to_close_app(self):
        intent, params = route_command("stop")
        self.assertEqual(intent, "close_app")
        self.assertEqual(params["app"], "last")

    def test_bare_mute_routes_to_volume(self):
        intent, params = route_command("mute")
        self.assertEqual(intent, "volume")
        self.assertEqual(params["action"], "mute")

    def test_bare_screenshot_routes(self):
        intent, _ = route_command("screenshot")
        self.assertEqual(intent, "screenshot")


# ---------------------------------------------------------------------------
# Fix 5: Planner conversation heuristic
# ---------------------------------------------------------------------------

class PlannerConversationHeuristicTest(unittest.TestCase):
    def test_greeting_routes_without_gemini(self):
        from agents.planner import _looks_like_conversation
        self.assertTrue(_looks_like_conversation("hi"))
        self.assertTrue(_looks_like_conversation("hello there"))
        self.assertTrue(_looks_like_conversation("hey bruh"))
        self.assertTrue(_looks_like_conversation("how are you doing"))

    def test_opinion_routes_without_gemini(self):
        from agents.planner import _looks_like_conversation
        self.assertTrue(_looks_like_conversation("do you like pizza"))
        self.assertTrue(_looks_like_conversation("can you help me"))
        self.assertTrue(_looks_like_conversation("are you smart"))

    def test_short_question_routes_without_gemini(self):
        from agents.planner import _looks_like_conversation
        self.assertTrue(_looks_like_conversation("you good?"))

    def test_technical_command_not_conversation(self):
        from agents.planner import _looks_like_conversation
        self.assertFalse(_looks_like_conversation("open spotify and play my playlist"))
        self.assertFalse(_looks_like_conversation("search for python tutorials on youtube"))


class PlannerShortChatFilesystemTest(unittest.TestCase):
    def test_create_commands_not_short_chat(self):
        from agents.planner import _looks_like_short_chat

        self.assertFalse(_looks_like_short_chat("create a folder name ghost"))
        self.assertFalse(_looks_like_short_chat("create a new file name download"))

    def test_copy_not_short_chat(self):
        from agents.planner import _looks_like_short_chat

        self.assertFalse(_looks_like_short_chat("copy ghost to desktop"))

    def test_profile_still_short_chat_when_short(self):
        from agents.planner import _looks_like_short_chat

        self.assertTrue(_looks_like_short_chat("check my profile"))


# ---------------------------------------------------------------------------
# Fix 2+3: Personality prompt rules
# ---------------------------------------------------------------------------

class PersonalityOverhaulTest(unittest.TestCase):
    def test_prompt_enforces_short_responses(self):
        lower = BRUH_SYSTEM_PROMPT.lower()
        self.assertIn("30 words", lower)
        self.assertIn("1-2 sentences", lower)

    def test_prompt_forbids_chatbot_filler(self):
        lower = BRUH_SYSTEM_PROMPT.lower()
        self.assertIn("certainly", lower)
        self.assertIn("absolutely", lower)

    def test_prompt_has_example_exchanges(self):
        self.assertIn("User:", BRUH_SYSTEM_PROMPT)
        self.assertIn("→", BRUH_SYSTEM_PROMPT)

    def test_prompt_mentions_voice(self):
        lower = BRUH_SYSTEM_PROMPT.lower()
        self.assertIn("spoken aloud", lower)

    def test_prompt_mentions_conversation_history(self):
        lower = BRUH_SYSTEM_PROMPT.lower()
        self.assertIn("conversation history", lower)

    def test_detail_mode_detection(self):
        from agents.personality import _wants_detail
        self.assertTrue(_wants_detail("tell me about python"))
        self.assertTrue(_wants_detail("explain recursion"))
        self.assertTrue(_wants_detail("go on"))
        self.assertTrue(_wants_detail("tell me more about that"))
        self.assertTrue(_wants_detail("elaborate on that"))
        self.assertFalse(_wants_detail("open chrome"))
        self.assertFalse(_wants_detail("play music"))
        self.assertFalse(_wants_detail("thanks"))


# ---------------------------------------------------------------------------
# Fix 1: Voice parameter values
# ---------------------------------------------------------------------------

class VoiceParameterTest(unittest.TestCase):
    def test_pause_threshold(self):
        from voice.input import PAUSE_THRESHOLD
        self.assertEqual(PAUSE_THRESHOLD, 1.5)

    def test_non_speaking_duration(self):
        from voice.input import NON_SPEAKING_DURATION
        self.assertEqual(NON_SPEAKING_DURATION, 0.5)

    def test_listen_timeout(self):
        from voice.input import LISTEN_TIMEOUT
        self.assertEqual(LISTEN_TIMEOUT, 8)

    def test_phrase_time_limit(self):
        from voice.input import PHRASE_TIME_LIMIT
        self.assertEqual(PHRASE_TIME_LIMIT, 15)

    def test_ambient_duration(self):
        from voice.input import AMBIENT_DURATION
        self.assertEqual(AMBIENT_DURATION, 1.2)

    def test_wake_timeout(self):
        from voice.input import WAKE_TIMEOUT
        self.assertEqual(WAKE_TIMEOUT, 3)

    def test_wake_phrase_limit(self):
        from voice.input import WAKE_PHRASE_LIMIT
        self.assertEqual(WAKE_PHRASE_LIMIT, 4)


class WakeListenerTest(unittest.TestCase):
    def test_listen_for_wake_word_importable(self):
        from voice.input import listen_for_wake_word
        self.assertTrue(callable(listen_for_wake_word))

    def test_wake_listener_returns_none_on_timeout(self):
        recognizer = mock.Mock()
        recognizer.listen.side_effect = voice_input.sr.WaitTimeoutError()
        recognizer.adjust_for_ambient_noise.return_value = None

        mic_ctx = mock.Mock()
        mic_ctx.__enter__ = mock.Mock(return_value=mock.Mock())
        mic_ctx.__exit__ = mock.Mock(return_value=False)

        with mock.patch.object(voice_input, "_recognizer", recognizer), \
             mock.patch.object(voice_input, "_calibrated", True), \
             mock.patch.object(voice_input.sr, "Microphone", return_value=mic_ctx):
            result = voice_input.listen_for_wake_word()
            self.assertIsNone(result)

    def test_wake_listener_returns_none_for_non_wake_word(self):
        recognizer = mock.Mock()
        recognizer.adjust_for_ambient_noise.return_value = None
        recognizer.listen.return_value = mock.Mock()
        recognizer.recognize_google = mock.Mock(return_value="open chrome")

        mic_ctx = mock.Mock()
        mic_ctx.__enter__ = mock.Mock(return_value=mock.Mock())
        mic_ctx.__exit__ = mock.Mock(return_value=False)

        with mock.patch.object(voice_input, "_recognizer", recognizer), \
             mock.patch.object(voice_input, "_calibrated", True), \
             mock.patch.object(voice_input.sr, "Microphone", return_value=mic_ctx):
            result = voice_input.listen_for_wake_word()
            self.assertIsNone(result)

    def test_wake_listener_returns_text_for_wake_word(self):
        recognizer = mock.Mock()
        recognizer.adjust_for_ambient_noise.return_value = None
        recognizer.listen.return_value = mock.Mock()
        recognizer.recognize_google = mock.Mock(return_value="Hey Bro")

        mic_ctx = mock.Mock()
        mic_ctx.__enter__ = mock.Mock(return_value=mock.Mock())
        mic_ctx.__exit__ = mock.Mock(return_value=False)

        with mock.patch.object(voice_input, "_recognizer", recognizer), \
             mock.patch.object(voice_input, "_calibrated", True), \
             mock.patch.object(voice_input.sr, "Microphone", return_value=mic_ctx):
            result = voice_input.listen_for_wake_word()
            self.assertEqual(result, "hey bro")


# ---------------------------------------------------------------------------
# Fix 6: Deeper history + truncation
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Screen pipeline routing — no false positives
# ---------------------------------------------------------------------------

class ScreenRoutingNoFalsePositiveTest(unittest.TestCase):
    def test_weather_not_screen(self):
        intent, _ = route_command("what is the weather")
        self.assertNotEqual(intent, "analyze_context")

    def test_why_conversational_not_screen(self):
        intent, _ = route_command("why are you so slow")
        self.assertNotEqual(intent, "analyze_context")

    def test_explain_python_not_screen(self):
        intent, _ = route_command("explain python decorators")
        self.assertNotEqual(intent, "analyze_context")

    def test_what_is_python_not_screen(self):
        intent, _ = route_command("what is python")
        self.assertNotEqual(intent, "analyze_context")


# ---------------------------------------------------------------------------
# Screen pipeline safety
# ---------------------------------------------------------------------------

class ScreenPipelineSafetyTest(unittest.TestCase):
    def test_analyze_context_returns_string_on_success(self):
        with mock.patch("agents.execution.capture_screen", return_value="test.png"), \
             mock.patch("agents.execution.extract_text", return_value="Hello world code here test text for analysis"), \
             mock.patch("agents.execution.ask_gemini", return_value="You're looking at code"):
            result = execute("analyze_context", {"query": "what am i looking at"})
            self.assertEqual(result, "You're looking at code")

    def test_analyze_context_returns_fallback_on_exception(self):
        with mock.patch("agents.execution.capture_screen", side_effect=RuntimeError("boom")):
            result = execute("analyze_context", {"query": "what am i looking at"})
            self.assertIn("Screen analysis broke", result)

    def test_analyze_context_returns_fallback_on_empty_ocr(self):
        with mock.patch("agents.execution.capture_screen", return_value="test.png"), \
             mock.patch("agents.execution.extract_text", return_value=""):
            result = execute("analyze_context", {"query": "what am i looking at"})
            self.assertIn("Can't see much", result)

    def test_analyze_context_returns_fallback_on_garbage_ocr(self):
        with mock.patch("agents.execution.capture_screen", return_value="test.png"), \
             mock.patch("agents.execution.extract_text", return_value="@@##$$%%&&**!!"):
            result = execute("analyze_context", {"query": "what am i looking at"})
            self.assertIn("Can't see much", result)


# ---------------------------------------------------------------------------
# OCR trimming
# ---------------------------------------------------------------------------

class OcrTrimmingTest(unittest.TestCase):
    def test_trim_ocr_caps_length(self):
        from agents.execution import _trim_ocr
        long_text = "a" * 5000
        result = _trim_ocr(long_text)
        self.assertLessEqual(len(result), 1000)

    def test_trim_ocr_empty(self):
        from agents.execution import _trim_ocr
        self.assertEqual(_trim_ocr(""), "")
        self.assertEqual(_trim_ocr(None), "")

    def test_useless_ocr_detection(self):
        from agents.execution import _is_useless_ocr
        self.assertTrue(_is_useless_ocr(""))
        self.assertTrue(_is_useless_ocr("   "))
        self.assertTrue(_is_useless_ocr("@@##$$"))
        self.assertFalse(_is_useless_ocr("This is a normal paragraph of text with enough words to pass the check."))


class DeeperHistoryTest(unittest.TestCase):
    def test_history_limit_is_eight(self):
        self.assertEqual(context_mod._HISTORY_LIMIT, 8)

    def test_format_context_truncates_long_responses(self):
        orig = dict(context_mod.context)
        try:
            long_resp = "A" * 400
            context_mod.context.update({
                "last_command": None, "last_response": None,
                "last_screen_text": None, "last_updated_at": None,
                "history": [
                    {"command": "test", "response": long_resp, "timestamp": "t", "screen_text": None},
                ],
            })
            result = context_mod.format_context()
            self.assertIn("A" * 200 + "...", result)
            self.assertNotIn("A" * 201 + "...", result.replace("A" * 200 + "...", ""))
        finally:
            context_mod.context.update(orig)


if __name__ == "__main__":
    unittest.main()
