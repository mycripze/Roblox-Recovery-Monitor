import ctypes
import json
import os
import queue
import threading
import time
import tkinter as tk
from collections.abc import Callable
from ctypes import wintypes
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


if os.name != "nt":
    raise SystemExit("Roblox Recovery Monitor runs on Windows.")

try:
    ctypes.windll.user32.SetProcessDPIAware()
except (AttributeError, OSError):
    pass


APP_NAME = "Roblox Recovery Monitor"
PROCESS_NAME = "RobloxPlayerBeta.exe"
MAX_ATTEMPTS = 3
OPEN_TIMEOUT_SECONDS = 60
REQUIRED_OPEN_SECONDS = 5
KEY_HOLD_SECONDS = 0.05
MOUSE_MOVE_SAMPLE_SECONDS = 0.02
MOUSE_MOVE_SAMPLE_DISTANCE = 2
MAX_RECORDED_DELAY_SECONDS = 10
MIN_REPLAY_SPEED = 0.25
MAX_REPLAY_SPEED = 10.0
DEFAULT_REPLAY_SPEED = 1.0
MIN_OPEN_TIMEOUT_SECONDS = 1
MAX_OPEN_TIMEOUT_SECONDS = 3600
MIN_POST_OPEN_WAIT_SECONDS = 0
MAX_POST_OPEN_WAIT_SECONDS = 600
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207
WM_MOUSEWHEEL = 0x020A
HC_ACTION = 0
WH_MOUSE_LL = 14
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000
INPUT_MOUSE = 0
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SW_RESTORE = 9
LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    HOOKPROC,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, WPARAM, LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.SetActiveWindow.argtypes = [wintypes.HWND]
user32.SetActiveWindow.restype = wintypes.HWND
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESSENTRY32W),
]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESSENTRY32W),
]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise OSError("Windows did not provide a LOCALAPPDATA folder.")
    folder = Path(base) / "RobloxRecoveryMonitor"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_json(path: Path, data: object) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def find_default_shortcut() -> str:
    desktop_paths = [
        Path.home() / "Desktop",
        Path.home() / "OneDrive" / "Desktop",
        Path("C:/Users/Public/Desktop"),
    ]
    for desktop in desktop_paths:
        if not desktop.is_dir():
            continue
        try:
            for entry in desktop.iterdir():
                lowered = entry.stem.casefold()
                if entry.suffix.casefold() == ".lnk" and (
                    "roblox player" in lowered or lowered == "roblox"
                ):
                    return str(entry)
        except OSError:
            continue
    return ""


def roblox_process_ids() -> set[int]:
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid_handle:
        raise ctypes.WinError()
    found: set[int] = set()
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while has_entry:
            if entry.szExeFile.casefold() == PROCESS_NAME.casefold():
                found.add(int(entry.th32ProcessID))
            has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return found


def roblox_is_running() -> bool:
    return bool(roblox_process_ids())


def window_process_id(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def process_image_name(pid: int) -> str:
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return ""
        return Path(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)


def client_screen_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    origin = POINT(rect.left, rect.top)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    return origin.x, origin.y, width, height


def find_roblox_window() -> int | None:
    best: tuple[int, int] | None = None
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    def visit(hwnd: int, _parameter: int) -> bool:
        nonlocal best
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = window_process_id(hwnd)
        if not pid or process_image_name(pid).casefold() != PROCESS_NAME.casefold():
            return True
        rect = client_screen_rect(hwnd)
        if rect is None:
            return True
        area = rect[2] * rect[3]
        if best is None or area > best[0]:
            best = (area, int(hwnd))
        return True

    callback = enum_proc_type(visit)
    if not user32.EnumWindows(callback, 0):
        raise ctypes.WinError()
    return best[1] if best else None


class MouseRecorder:
    def __init__(self, on_change, on_error):
        self.on_change = on_change
        self.on_error = on_error
        self.actions: list[dict] = []
        self.recording = False
        self._hook = None
        self._hook_proc = HOOKPROC(self._handle_event)
        self._last_action_time = 0.0
        self._last_move_time = 0.0
        self._last_recorded_point: tuple[int, int] | None = None
        self._foreground_hwnd = 0
        self._foreground_is_roblox = False
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.recording:
            return
        module = kernel32.GetModuleHandleW(None)
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._hook_proc, module, 0)
        if not hook:
            raise ctypes.WinError()
        self.actions = []
        self._last_action_time = 0.0
        self._last_move_time = 0.0
        self._last_recorded_point = None
        self._foreground_hwnd = 0
        self._foreground_is_roblox = False
        self._hook = hook
        self.recording = True
        self.on_change()

    def stop(self) -> list[dict]:
        if self._hook:
            if not user32.UnhookWindowsHookEx(self._hook):
                raise ctypes.WinError()
            self._hook = None
        self.recording = False
        self.on_change()
        with self._lock:
            return list(self.actions)

    def _handle_event(self, code, message, data_pointer):
        if code == HC_ACTION and self.recording:
            button = {
                WM_LBUTTONDOWN: "left",
                WM_RBUTTONDOWN: "right",
                WM_MBUTTONDOWN: "middle",
            }.get(message)
            is_move = message == WM_MOUSEMOVE
            if button or message == WM_MOUSEWHEEL or is_move:
                try:
                    details = ctypes.cast(
                        data_pointer, ctypes.POINTER(MSLLHOOKSTRUCT)
                    ).contents
                    hwnd = user32.GetForegroundWindow()
                    if hwnd != self._foreground_hwnd:
                        self._foreground_hwnd = hwnd
                        self._foreground_is_roblox = (
                            process_image_name(window_process_id(hwnd)).casefold()
                            == PROCESS_NAME.casefold()
                        )
                    if self._foreground_is_roblox:
                        rect = client_screen_rect(hwnd)
                        if rect:
                            left, top, width, height = rect
                            x = (details.pt.x - left) / width
                            y = (details.pt.y - top) / height
                            if 0 <= x <= 1 and 0 <= y <= 1:
                                now = time.monotonic()
                                point = (details.pt.x, details.pt.y)
                                if is_move and self._last_recorded_point is not None:
                                    moved_x = point[0] - self._last_recorded_point[0]
                                    moved_y = point[1] - self._last_recorded_point[1]
                                    if (
                                        moved_x * moved_x + moved_y * moved_y
                                        < MOUSE_MOVE_SAMPLE_DISTANCE**2
                                        and now - self._last_move_time
                                        < MOUSE_MOVE_SAMPLE_SECONDS
                                    ):
                                        return user32.CallNextHookEx(
                                            self._hook, code, message, data_pointer
                                        )
                                delay = min(
                                    max(now - self._last_action_time, 0.0),
                                    MAX_RECORDED_DELAY_SECONDS,
                                )
                                action = {
                                    "type": (
                                        "move"
                                        if is_move
                                        else "scroll"
                                        if message == WM_MOUSEWHEEL
                                        else "click"
                                    ),
                                    "x": round(x, 6),
                                    "y": round(y, 6),
                                    "delay": round(delay, 3),
                                }
                                if button:
                                    action["button"] = button
                                else:
                                    raw_delta = (details.mouseData >> 16) & 0xFFFF
                                    action["delta"] = ctypes.c_short(raw_delta).value
                                with self._lock:
                                    self.actions.append(action)
                                    self._last_action_time = now
                                    self._last_recorded_point = point
                                    if is_move:
                                        self._last_move_time = now
                except (OSError, ValueError) as error:
                    self.on_error(error)
        return user32.CallNextHookEx(self._hook, code, message, data_pointer)


class RobloxRecoveryApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x900")
        self.root.minsize(900, 800)
        self.folder = app_data_dir()
        self.settings_path = self.folder / "settings.json"
        self.macro_path = self.folder / "actions.json"
        self.history_path = self.folder / "history.json"
        self.monitoring_sessions_path = self.folder / "monitoring_sessions.json"
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.monitoring_sessions: list[dict] = []
        self.monitor_session_started_at: datetime | None = None
        self.monitor_session_started_monotonic: float | None = None
        self.stopwatch_after: str | None = None
        self.shortcut = tk.StringVar(value=find_default_shortcut())
        self.history_path_var = tk.StringVar(value=str(self.history_path))
        self.monitoring_sessions_path_var = tk.StringVar(
            value=str(self.monitoring_sessions_path)
        )
        self.replay_speed = tk.DoubleVar(value=DEFAULT_REPLAY_SPEED)
        self.replay_speed_text = tk.StringVar(value=f"{DEFAULT_REPLAY_SPEED:.2f}x")
        self.open_timeout_text = tk.StringVar(value=str(OPEN_TIMEOUT_SECONDS))
        self.post_open_wait_text = tk.StringVar(value=str(REQUIRED_OPEN_SECONDS))
        self.monitor_setting_entries: list[ttk.Entry] = []
        self.hotkey_modifiers = {"ctrl", "shift"}
        self.hotkey_key = "r"
        self.hotkey_capture = False
        self.status = tk.StringVar(value="Not monitoring")
        self.stopwatch_text = tk.StringVar(value="Elapsed: 00:00:00")
        self.record_status = tk.StringVar(value="No action recording")
        self.macro: list[dict] = []
        self.history: list[dict] = []
        self._settings_save_after: str | None = None
        self.recorder = MouseRecorder(self._update_record_label, self._recording_error)
        self._hotkey_down = False
        self._last_hotkey_time = 0.0

        self._configure_dark_theme()
        self._load_settings()
        self.history_path = Path(
            os.path.expandvars(self.history_path_var.get().strip())
        ).expanduser()
        self.monitoring_sessions_path = Path(
            os.path.expandvars(self.monitoring_sessions_path_var.get().strip())
        ).expanduser()
        self._load_macro()
        self._build_ui()
        self._update_record_label()
        self._load_history()
        self._load_monitoring_sessions()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(100, self._process_messages)
        self.root.after(50, self._poll_hotkey)

    def _configure_dark_theme(self) -> None:
        self.colors = {
            "background": "#111318",
            "surface": "#191d24",
            "field": "#101319",
            "foreground": "#e8edf5",
            "muted": "#9ba6b7",
            "border": "#2b323e",
            "hover": "#252c38",
            "selected": "#204b78",
            "green": "#56d39b",
            "red": "#ff7785",
            "accent": "#69a7ff",
        }
        self.root.configure(background=self.colors["background"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            ".",
            background=self.colors["background"],
            foreground=self.colors["foreground"],
            fieldbackground=self.colors["field"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            troughcolor=self.colors["field"],
            focuscolor=self.colors["accent"],
        )
        style.configure("TFrame", background=self.colors["background"])
        style.configure("Card.TFrame", background=self.colors["surface"])
        style.configure(
            "TLabelframe",
            background=self.colors["surface"],
            bordercolor=self.colors["border"],
            padding=12,
        )
        style.configure(
            "TLabelframe.Label",
            background=self.colors["surface"],
            foreground=self.colors["foreground"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "TLabel",
            background=self.colors["background"],
            foreground=self.colors["foreground"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Card.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["foreground"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Muted.TLabel",
            background=self.colors["background"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "CardMuted.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Title.TLabel",
            background=self.colors["background"],
            foreground=self.colors["foreground"],
            font=("Segoe UI Semibold", 20),
        )
        style.configure(
            "Section.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["foreground"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Success.Card.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["green"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Failure.Card.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["red"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "TButton",
            background=self.colors["surface"],
            foreground=self.colors["foreground"],
            bordercolor=self.colors["border"],
            padding=(12, 8),
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Primary.TButton",
            background=self.colors["accent"],
            foreground="#0f1722",
            bordercolor=self.colors["accent"],
        )
        style.map(
            "TButton",
            background=[
                ("disabled", self.colors["surface"]),
                ("pressed", self.colors["selected"]),
                ("active", self.colors["hover"]),
            ],
            foreground=[("disabled", self.colors["muted"])],
        )
        style.map(
            "Primary.TButton",
            background=[
                ("disabled", self.colors["border"]),
                ("pressed", "#4b8ee6"),
                ("active", "#83b7ff"),
            ],
        )
        style.configure(
            "TEntry",
            background=self.colors["field"],
            fieldbackground=self.colors["field"],
            foreground=self.colors["foreground"],
            insertcolor=self.colors["foreground"],
            bordercolor=self.colors["border"],
            padding=(8, 7),
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview",
            background=self.colors["field"],
            fieldbackground=self.colors["field"],
            foreground=self.colors["foreground"],
            bordercolor=self.colors["border"],
            rowheight=26,
            font=("Segoe UI", 9),
        )
        style.map(
            "Treeview",
            background=[("selected", self.colors["selected"])],
            foreground=[("selected", self.colors["foreground"])],
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["surface"],
            foreground=self.colors["muted"],
            bordercolor=self.colors["border"],
            padding=(8, 6),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", self.colors["hover"])],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=self.colors["surface"],
            troughcolor=self.colors["background"],
            bordercolor=self.colors["border"],
            arrowcolor=self.colors["foreground"],
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=(24, 20))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Monitor Roblox, replay your saved actions, and review relaunches.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        launcher_frame = ttk.Frame(outer, style="Card.TFrame", padding=14)
        launcher_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(
            launcher_frame, text="Roblox Player shortcut", style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 9))
        launcher_row = ttk.Frame(launcher_frame, style="Card.TFrame")
        launcher_row.pack(fill="x")
        shortcut_entry = ttk.Entry(launcher_row, textvariable=self.shortcut)
        shortcut_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(
            launcher_row, text="Browse", command=self._browse_shortcut
        ).pack(side="left")

        controls = ttk.Frame(outer, style="Card.TFrame", padding=(14, 12))
        controls.pack(fill="x", pady=(0, 10))
        self.start_button = ttk.Button(
            controls,
            text="Start monitoring",
            command=self._start_monitoring,
            style="Primary.TButton",
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            controls,
            text="Stop monitoring",
            command=self._stop_monitoring,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=(8, 18))
        self.record_button = ttk.Button(
            controls,
            text=f"Record actions ({self._hotkey_display()})",
            command=self._toggle_recording,
        )
        self.record_button.pack(side="left")
        ttk.Label(
            controls, textvariable=self.status, style="Card.TLabel"
        ).pack(side="left", padx=(18, 0))
        ttk.Label(
            controls,
            textvariable=self.stopwatch_text,
            style="Card.TLabel",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(14, 0))
        ttk.Label(
            controls, textvariable=self.record_status, style="CardMuted.TLabel"
        ).pack(side="right")

        settings_frame = ttk.Frame(outer, style="Card.TFrame", padding=14)
        settings_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(
            settings_frame, text="Replay and monitoring settings", style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 10))

        speed_row = ttk.Frame(settings_frame, style="Card.TFrame")
        speed_row.pack(fill="x")
        ttk.Label(speed_row, text="Mouse glide speed", style="Card.TLabel").pack(
            side="left", padx=(0, 16)
        )
        ttk.Label(speed_row, text="Slower", style="CardMuted.TLabel").pack(
            side="left", padx=(0, 4)
        )
        self.replay_speed_scale = tk.Scale(
            speed_row,
            from_=MIN_REPLAY_SPEED,
            to=MAX_REPLAY_SPEED,
            resolution=0.25,
            orient="horizontal",
            showvalue=False,
            variable=self.replay_speed,
            command=self._on_replay_speed_change,
            length=340,
            highlightthickness=0,
            background=self.colors["background"],
            foreground=self.colors["foreground"],
            troughcolor=self.colors["field"],
            activebackground=self.colors["accent"],
            highlightbackground=self.colors["background"],
            highlightcolor=self.colors["accent"],
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        self.replay_speed_scale.pack(side="left", fill="x", expand=True)
        self.replay_speed_text.set(f"{self.replay_speed.get():.2f}x")
        ttk.Label(speed_row, text="Faster", style="CardMuted.TLabel").pack(
            side="left", padx=(4, 10)
        )
        ttk.Label(
            speed_row, textvariable=self.replay_speed_text, style="Card.TLabel"
        ).pack(side="left", padx=(0, 8))
        ttk.Label(speed_row, text="1.00x = recorded pace", style="CardMuted.TLabel").pack(
            side="left"
        )

        timing_row = ttk.Frame(settings_frame, style="Card.TFrame")
        timing_row.pack(fill="x", pady=(10, 0))
        self._add_seconds_input(
            timing_row,
            self.open_timeout_text,
            "Open timeout",
            MIN_OPEN_TIMEOUT_SECONDS,
            MAX_OPEN_TIMEOUT_SECONDS,
        )
        self._add_seconds_input(
            timing_row,
            self.post_open_wait_text,
            "Wait after Roblox opens",
            MIN_POST_OPEN_WAIT_SECONDS,
            MAX_POST_OPEN_WAIT_SECONDS,
        )

        hotkey_row = ttk.Frame(settings_frame, style="Card.TFrame")
        hotkey_row.pack(fill="x", pady=(10, 0))
        ttk.Label(
            hotkey_row,
            text="Recorder shortcut",
            style="Card.TLabel",
        ).pack(side="left", padx=(0, 12))
        self.hotkey_entry = ttk.Entry(hotkey_row, state="readonly", width=22)
        self.hotkey_entry.pack(side="left", padx=(0, 12))
        self.hotkey_entry.bind("<Button-1>", self._begin_hotkey_capture)
        self.hotkey_entry.bind("<FocusIn>", self._begin_hotkey_capture)
        ttk.Label(
            hotkey_row,
            text="Click to set; use Ctrl, Shift, or Alt with a key.",
            style="CardMuted.TLabel",
        ).pack(side="left")
        self._show_hotkey_in_entry()

        sessions_frame = ttk.Frame(outer, style="Card.TFrame", padding=14)
        sessions_frame.pack(fill="x", pady=(0, 10))
        sessions_header = ttk.Frame(sessions_frame, style="Card.TFrame")
        sessions_header.pack(fill="x", pady=(0, 8))
        ttk.Label(
            sessions_header, text="Monitoring Sessions", style="Section.TLabel"
        ).pack(side="left")
        ttk.Label(
            sessions_header,
            text="A record is added when monitoring stops.",
            style="CardMuted.TLabel",
        ).pack(side="left", padx=(10, 0))
        self.clear_sessions_button = ttk.Button(
            sessions_header,
            text="Clear sessions",
            command=self._open_clear_sessions_dialog,
        )
        self.clear_sessions_button.pack(side="right")
        sessions_location = ttk.Frame(sessions_frame, style="Card.TFrame")
        sessions_location.pack(fill="x", pady=(0, 8))
        ttk.Label(
            sessions_location, text="Save location", style="CardMuted.TLabel"
        ).pack(side="left", padx=(0, 10))
        self.sessions_path_entry = ttk.Entry(
            sessions_location, textvariable=self.monitoring_sessions_path_var
        )
        self.sessions_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.sessions_path_entry.bind("<Return>", self._apply_monitoring_sessions_path)
        self.sessions_path_entry.bind("<FocusOut>", self._apply_monitoring_sessions_path)
        self.sessions_browse_button = ttk.Button(
            sessions_location,
            text="Browse",
            command=self._browse_monitoring_sessions_path,
        )
        self.sessions_browse_button.pack(side="left")
        session_columns = ("date", "started", "ended", "elapsed")
        self.sessions_table = ttk.Treeview(
            sessions_frame,
            columns=session_columns,
            show="headings",
            height=3,
        )
        for column, heading, width in (
            ("date", "Date", 130),
            ("started", "Time started", 150),
            ("ended", "Time ended", 150),
            ("elapsed", "Elapsed Time", 150),
        ):
            self.sessions_table.heading(column, text=heading)
            self.sessions_table.column(
                column, width=width, minwidth=80, anchor="w", stretch=True
            )
        session_scrollbar = ttk.Scrollbar(
            sessions_frame, orient="vertical", command=self.sessions_table.yview
        )
        self.sessions_table.configure(yscrollcommand=session_scrollbar.set)
        self.sessions_table.pack(side="left", fill="x", expand=True)
        session_scrollbar.pack(side="right", fill="y")
        self._render_monitoring_sessions()

        history_frame = ttk.Frame(outer, style="Card.TFrame", padding=14)
        self.history_panel = history_frame
        history_frame.pack(fill="both", expand=True)
        history_header = ttk.Frame(history_frame, style="Card.TFrame")
        history_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(
            history_header, text="Relaunch history", style="Section.TLabel"
        ).pack(side="left")
        ttk.Button(
            history_header, text="Clear history", command=self._open_clear_history_dialog
        ).pack(side="right")
        history_location = ttk.Frame(history_frame, style="Card.TFrame")
        self.history_location = history_location
        history_location.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(
            history_location, text="Save location", style="CardMuted.TLabel"
        ).pack(side="left", padx=(0, 10))
        self.history_entry = ttk.Entry(
            history_location, textvariable=self.history_path_var
        )
        self.history_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.history_entry.bind("<Return>", self._apply_history_path)
        self.history_entry.bind("<FocusOut>", self._apply_history_path)
        ttk.Button(
            history_location, text="Browse", command=self._browse_history_path
        ).pack(side="left")

        self.history_body = ttk.Frame(history_frame, style="Card.TFrame")
        self.history_body.place(x=14, y=90, width=100, height=100)
        self.log = tk.Text(
            self.history_body,
            width=1,
            wrap="char",
            background=self.colors["field"],
            foreground=self.colors["foreground"],
            insertbackground=self.colors["foreground"],
            selectbackground=self.colors["selected"],
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            state="disabled",
        )
        history_scrollbar = ttk.Scrollbar(
            self.history_body, orient="vertical", command=self.log.yview
        )
        self.log.configure(yscrollcommand=history_scrollbar.set)
        self.log.tag_configure(
            "SUCCESSFUL",
            foreground=self.colors["green"],
            font=("Segoe UI", 9, "bold"),
        )
        self.log.tag_configure(
            "FAILED",
            foreground=self.colors["red"],
            font=("Segoe UI", 9, "bold"),
        )
        self.log.tag_configure(
            "META",
            foreground=self.colors["foreground"],
            font=("Segoe UI", 9, "bold"),
        )
        self.log.tag_configure("REASON", foreground=self.colors["muted"])
        self.log.tag_configure("EMPTY", foreground=self.colors["muted"])
        self.log.place(relx=0, rely=0, relwidth=1, relheight=1, width=-18)
        history_scrollbar.place(relx=1, rely=0, relheight=1, anchor="ne")
        history_frame.columnconfigure(0, weight=1)
        history_frame.bind("<Configure>", self._layout_history_body)
        history_frame.after_idle(self._layout_history_body)
        self._render_history()

    def _add_seconds_input(
        self,
        parent: ttk.Frame,
        variable: tk.StringVar,
        label: str,
        minimum: int,
        maximum: int,
    ) -> ttk.Entry:
        field = ttk.Frame(parent, style="Card.TFrame")
        field.pack(side="left", padx=(0, 24))
        ttk.Label(field, text=label, style="CardMuted.TLabel").pack(
            side="left", padx=(0, 8)
        )
        entry = ttk.Entry(field, textvariable=variable, width=7, justify="right")
        self.monitor_setting_entries.append(entry)
        entry.pack(side="left")
        entry.bind(
            "<FocusOut>",
            lambda _event, value=variable, low=minimum, high=maximum: self._normalize_seconds(
                value, low, high
            ),
        )
        entry.bind(
            "<Return>",
            lambda _event, value=variable, low=minimum, high=maximum: self._normalize_seconds(
                value, low, high
            ),
        )
        ttk.Label(field, text="s", style="CardMuted.TLabel").pack(side="left", padx=(5, 0))
        return entry

    def _hotkey_display(self) -> str:
        names = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt"}
        key = self.hotkey_key
        if len(key) == 1:
            key = key.upper()
        else:
            key = key.replace("prior", "PageUp").replace("next", "PageDown").title()
        return "+".join([*(names[name] for name in ("ctrl", "shift", "alt") if name in self.hotkey_modifiers), key])

    @staticmethod
    def _key_virtual_code(key: str) -> int | None:
        normalized = key.casefold()
        if len(normalized) == 1 and normalized.isascii() and normalized.isalnum():
            return ord(normalized.upper())
        if normalized.startswith("f") and normalized[1:].isdigit():
            number = int(normalized[1:])
            if 1 <= number <= 24:
                return 0x70 + number - 1
        return {
            "space": 0x20,
            "tab": 0x09,
            "return": 0x0D,
            "backspace": 0x08,
            "delete": 0x2E,
            "insert": 0x2D,
            "home": 0x24,
            "end": 0x23,
            "prior": 0x21,
            "next": 0x22,
            "left": 0x25,
            "up": 0x26,
            "right": 0x27,
            "down": 0x28,
            "minus": 0xBD,
            "equal": 0xBB,
            "bracketleft": 0xDB,
            "bracketright": 0xDD,
            "backslash": 0xDC,
            "semicolon": 0xBA,
            "apostrophe": 0xDE,
            "grave": 0xC0,
            "comma": 0xBC,
            "period": 0xBE,
            "slash": 0xBF,
        }.get(normalized)

    @staticmethod
    def _pressed_hotkey_modifiers() -> set[str]:
        modifier_codes = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12}
        return {
            name
            for name, code in modifier_codes.items()
            if user32.GetAsyncKeyState(code) & 0x8000
        }

    def _show_hotkey_in_entry(self) -> None:
        if not hasattr(self, "hotkey_entry"):
            return
        self.hotkey_entry.configure(state="normal")
        self.hotkey_entry.delete(0, "end")
        self.hotkey_entry.insert(0, self._hotkey_display())
        self.hotkey_entry.configure(state="readonly")

    def _begin_hotkey_capture(self, _event=None):
        if self.hotkey_capture:
            return "break"
        self.hotkey_capture = True
        self.hotkey_entry.configure(state="normal")
        self.hotkey_entry.delete(0, "end")
        self.hotkey_entry.insert(0, "Press your shortcut...")
        self.hotkey_entry.focus_set()
        self._hotkey_binding_id = self.root.bind(
            "<KeyPress>", self._capture_hotkey_key, add="+"
        )
        return "break"

    def _capture_hotkey_key(self, event):
        key = event.keysym.casefold()
        if key == "escape":
            self.hotkey_capture = False
            self.root.unbind("<KeyPress>", self._hotkey_binding_id)
            self._show_hotkey_in_entry()
            return "break"
        if key in ("control_l", "control_r", "shift_l", "shift_r", "alt_l", "alt_r"):
            return "break"
        modifiers = self._pressed_hotkey_modifiers()
        if not modifiers:
            self.hotkey_capture = False
            self.root.unbind("<KeyPress>", self._hotkey_binding_id)
            self._show_hotkey_in_entry()
            messagebox.showwarning(
                APP_NAME,
                "Choose a shortcut that includes Ctrl, Shift, or Alt to avoid "
                "triggering while typing.",
            )
            return "break"
        if self._key_virtual_code(key) is None:
            self.hotkey_capture = False
            self.root.unbind("<KeyPress>", self._hotkey_binding_id)
            self._show_hotkey_in_entry()
            messagebox.showwarning(APP_NAME, "That key is not supported.")
            return "break"
        self.hotkey_modifiers = modifiers
        self.hotkey_key = key
        self.hotkey_capture = False
        self.root.unbind("<KeyPress>", self._hotkey_binding_id)
        self._show_hotkey_in_entry()
        self._update_record_label()
        self._save_settings()
        return "break"

    def _normalize_seconds(
        self, variable: tk.StringVar, minimum: int, maximum: int
    ) -> None:
        value = variable.get().strip()
        if value.isdecimal():
            seconds = int(value)
            if minimum <= seconds <= maximum:
                variable.set(str(seconds))

    def _parse_seconds(
        self, variable: tk.StringVar, label: str, minimum: int, maximum: int
    ) -> int:
        value = variable.get().strip()
        if not value.isdecimal():
            raise ValueError(f"{label} must be a whole number of seconds.")
        seconds = int(value)
        if not minimum <= seconds <= maximum:
            raise ValueError(
                f"{label} must be between {minimum} and {maximum} seconds."
            )
        return seconds

    def _load_settings(self) -> None:
        if not self.settings_path.exists():
            return
        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            saved_path = settings.get("shortcut", "")
            if saved_path:
                self.shortcut.set(saved_path)
            saved_speed = settings.get("replay_speed", DEFAULT_REPLAY_SPEED)
            if (
                isinstance(saved_speed, (int, float))
                and not isinstance(saved_speed, bool)
                and MIN_REPLAY_SPEED <= saved_speed <= MAX_REPLAY_SPEED
            ):
                self.replay_speed.set(float(saved_speed))
            saved_history_path = settings.get("history_path")
            if isinstance(saved_history_path, str) and saved_history_path.strip():
                self.history_path_var.set(saved_history_path)
            saved_sessions_path = settings.get("monitoring_sessions_path")
            if isinstance(saved_sessions_path, str) and saved_sessions_path.strip():
                self.monitoring_sessions_path_var.set(saved_sessions_path)
            timeout = settings.get("open_timeout_seconds", OPEN_TIMEOUT_SECONDS)
            if isinstance(timeout, str) and timeout.isdecimal():
                timeout = int(timeout)
            if isinstance(timeout, int) and not isinstance(timeout, bool):
                if MIN_OPEN_TIMEOUT_SECONDS <= timeout <= MAX_OPEN_TIMEOUT_SECONDS:
                    self.open_timeout_text.set(str(timeout))
            wait = settings.get("post_open_wait_seconds", REQUIRED_OPEN_SECONDS)
            if isinstance(wait, str) and wait.isdecimal():
                wait = int(wait)
            if isinstance(wait, int) and not isinstance(wait, bool):
                if MIN_POST_OPEN_WAIT_SECONDS <= wait <= MAX_POST_OPEN_WAIT_SECONDS:
                    self.post_open_wait_text.set(str(wait))
            saved_hotkey = settings.get("record_hotkey")
            if isinstance(saved_hotkey, dict):
                modifiers = saved_hotkey.get("modifiers")
                key = saved_hotkey.get("key")
                if (
                    isinstance(modifiers, list)
                    and all(item in ("ctrl", "shift", "alt") for item in modifiers)
                    and modifiers
                    and isinstance(key, str)
                    and self._key_virtual_code(key) is not None
                ):
                    self.hotkey_modifiers = set(modifiers)
                    self.hotkey_key = key.casefold()
        except (OSError, json.JSONDecodeError) as error:
            detail = str(error)
            self.root.after(
                200,
                lambda detail=detail: messagebox.showwarning(
                    APP_NAME,
                    f"Settings could not be loaded from:\n{self.settings_path}\n\n{detail}",
                ),
            )

    def _load_macro(self) -> None:
        if not self.macro_path.exists():
            return
        try:
            data = json.loads(self.macro_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("The action recording must be a JSON list.")
            if any(not isinstance(action, dict) for action in data):
                raise ValueError("The action recording contains an invalid entry.")
            self.macro = data
        except (OSError, json.JSONDecodeError, ValueError) as error:
            detail = str(error)
            self.root.after(
                200,
                lambda detail=detail: messagebox.showwarning(
                    APP_NAME,
                    f"The saved action recording could not be loaded:\n{detail}",
                ),
            )

    def _load_history(self) -> None:
        self.history = []
        if not self.history_path.exists():
            self._render_history()
            return
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("The history file must contain a JSON list.")
            if any(
                not isinstance(entry, dict)
                or entry.get("status") not in ("SUCCESSFUL", "FAILED")
                for entry in data
            ):
                raise ValueError("The history file contains an invalid entry.")
            self.history = data
            self._render_history()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showwarning(
                APP_NAME,
                f"History could not be loaded from:\n{self.history_path}\n\n{error}",
            )
            self._render_history()

    def _browse_shortcut(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose the official Roblox Player shortcut",
            filetypes=[
                ("Windows shortcuts and applications", "*.lnk *.exe"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.shortcut.set(selected)
            self._save_settings()

    def _browse_history_path(self) -> None:
        current_path = Path(self.history_path_var.get().strip() or self.history_path)
        selected = filedialog.asksaveasfilename(
            title="Choose relaunch history file",
            initialdir=str(current_path.parent),
            initialfile=current_path.name,
            defaultextension=".json",
            filetypes=[("JSON history", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.history_path_var.set(selected)
            self._apply_history_path()

    def _browse_monitoring_sessions_path(self) -> None:
        current_path = Path(
            self.monitoring_sessions_path_var.get().strip()
            or self.monitoring_sessions_path
        )
        selected = filedialog.asksaveasfilename(
            title="Choose monitoring sessions file",
            initialdir=str(current_path.parent),
            initialfile=current_path.name,
            defaultextension=".json",
            filetypes=[("JSON sessions", "*.json"), ("All files", "*.*")],
        )
        if selected:
            self.monitoring_sessions_path_var.set(selected)
            self._apply_monitoring_sessions_path()

    def _apply_history_path(self, _event=None):
        raw_path = self.history_path_var.get().strip()
        try:
            if not raw_path:
                raise ValueError("Choose a file path for relaunch history.")
            selected = Path(os.path.expandvars(raw_path)).expanduser()
            if selected.exists() and selected.is_dir():
                raise ValueError("The history location must be a file, not a folder.")
            if not selected.parent.is_dir():
                raise ValueError(
                    "The parent folder for the history file does not exist."
                )
        except (OSError, ValueError) as error:
            messagebox.showerror(APP_NAME, f"Invalid history file location:\n\n{error}")
            self.history_path_var.set(str(self.history_path))
            return "break" if _event else False
        if selected != self.history_path:
            self.history_path = selected
            self._load_history()
        self._save_settings()
        return "break" if _event else True

    def _apply_monitoring_sessions_path(self, _event=None):
        raw_path = self.monitoring_sessions_path_var.get().strip()
        try:
            if not raw_path:
                raise ValueError("Choose a file path for monitoring sessions.")
            selected = Path(os.path.expandvars(raw_path)).expanduser()
            if selected.exists() and selected.is_dir():
                raise ValueError("The sessions location must be a file, not a folder.")
            if not selected.parent.is_dir():
                raise ValueError(
                    "The parent folder for the sessions file does not exist."
                )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                APP_NAME, f"Invalid monitoring sessions file location:\n\n{error}"
            )
            self.monitoring_sessions_path_var.set(
                str(self.monitoring_sessions_path)
            )
            return "break" if _event else False
        if selected != self.monitoring_sessions_path:
            self.monitoring_sessions_path = selected
            self.monitoring_sessions = []
            self._load_monitoring_sessions()
            self._render_monitoring_sessions()
        self._save_settings()
        return "break" if _event else True

    def _save_settings(self) -> None:
        if self._settings_save_after is not None:
            self.root.after_cancel(self._settings_save_after)
        self._settings_save_after = None
        try:
            write_json(
                self.settings_path,
                {
                    "shortcut": self.shortcut.get().strip(),
                    "replay_speed": float(self.replay_speed.get()),
                    "history_path": self.history_path_var.get().strip(),
                    "monitoring_sessions_path": (
                        self.monitoring_sessions_path_var.get().strip()
                    ),
                    "open_timeout_seconds": self.open_timeout_text.get().strip(),
                    "post_open_wait_seconds": self.post_open_wait_text.get().strip(),
                    "record_hotkey": {
                        "modifiers": [
                            name
                            for name in ("ctrl", "shift", "alt")
                            if name in self.hotkey_modifiers
                        ],
                        "key": self.hotkey_key,
                    },
                },
            )
        except OSError as error:
            messagebox.showerror(
                APP_NAME, f"Could not save settings:\n{self.settings_path}\n\n{error}"
            )

    def _on_replay_speed_change(self, value: str) -> None:
        speed = float(value)
        self.replay_speed_text.set(f"{speed:.2f}x")
        if self._settings_save_after is not None:
            self.root.after_cancel(self._settings_save_after)
        self._settings_save_after = self.root.after(
            400, self._save_scheduled_settings
        )

    def _save_scheduled_settings(self) -> None:
        self._settings_save_after = None
        self._save_settings()

    def _toggle_recording(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning(
                APP_NAME, "Stop monitoring before recording or changing the actions."
            )
            return
        if self.recorder.recording:
            self._finish_recording()
            return
        try:
            self.recorder.start()
        except OSError as error:
            messagebox.showerror(
                APP_NAME, f"Could not start the mouse recorder.\n\n{error}"
            )

    def _finish_recording(self) -> None:
        try:
            actions = self.recorder.stop()
            if not actions:
                messagebox.showwarning(
                    APP_NAME,
                    "No Roblox mouse actions were recorded. "
                    "Keep Roblox in the foreground while moving and clicking.",
                )
                return
            if not any(action.get("type") == "move" for action in actions):
                messagebox.showwarning(
                    APP_NAME,
                    "No mouse movement path was recorded. Start recording while "
                    "Roblox is open, then move the pointer along the path you want "
                    "replayed and click/scroll as needed.",
                )
                return
            self.macro = actions
            write_json(self.macro_path, self.macro)
            self._update_record_label()
            click_count = sum(action.get("type") == "click" for action in actions)
            scroll_count = sum(action.get("type") == "scroll" for action in actions)
            move_count = sum(action.get("type") == "move" for action in actions)
            messagebox.showinfo(
                APP_NAME,
                f"Saved {move_count} mouse path point(s), {click_count} click(s), "
                f"and {scroll_count} scroll(s).",
            )
        except OSError as error:
            messagebox.showerror(
                APP_NAME, f"Could not save the action recording.\n\n{error}"
            )

    def _update_record_label(self) -> None:
        click_count = sum(action.get("type") == "click" for action in self.macro)
        scroll_count = sum(action.get("type") == "scroll" for action in self.macro)
        move_count = sum(action.get("type") == "move" for action in self.macro)
        saved_summary = (
            f"{move_count} path point(s), {click_count} click(s), "
            f"{scroll_count} scroll(s) saved"
        )
        if hasattr(self, "record_button"):
            self.record_button.configure(
                text=(
                    f"Stop recording ({self._hotkey_display()})"
                    if self.recorder.recording
                    else f"Record actions ({self._hotkey_display()})"
                )
            )
        self.record_status.set(
            "Recording Roblox mouse actions..."
            if self.recorder.recording
            else saved_summary
            if self.macro
            else "No action recording"
        )

    def _recording_error(self, error: Exception) -> None:
        self.messages.put(("recording_error", str(error)))

    def _poll_hotkey(self) -> None:
        pressed_modifiers = self._pressed_hotkey_modifiers()
        key_code = self._key_virtual_code(self.hotkey_key)
        key_down = bool(key_code and user32.GetAsyncKeyState(key_code) & 0x8000)
        combination_down = (
            pressed_modifiers == self.hotkey_modifiers and key_down
        )
        now = time.monotonic()
        if (
            combination_down
            and not self._hotkey_down
            and now - self._last_hotkey_time > 0.5
            and not self.hotkey_capture
        ):
            self._last_hotkey_time = now
            self._toggle_recording()
        self._hotkey_down = combination_down
        self.root.after(50, self._poll_hotkey)

    def _start_monitoring(self) -> None:
        if self.recorder.recording:
            messagebox.showerror(
                APP_NAME, "Stop the action recorder before starting monitoring."
            )
            return
        shortcut = Path(self.shortcut.get().strip())
        if not shortcut.is_file():
            messagebox.showerror(
                APP_NAME,
                "Choose the official Roblox Player desktop shortcut (or its application) first.",
            )
            return
        if not self.macro:
            messagebox.showerror(
                APP_NAME,
                "Record the scroll/click actions in Roblox before starting monitoring.",
            )
            return
        if not any(action.get("type") == "move" for action in self.macro):
            messagebox.showerror(
                APP_NAME,
                "The saved recording has no mouse movement path. Re-record while "
                "moving the pointer through the desired Roblox path.",
            )
            return
        try:
            open_timeout = self._parse_seconds(
                self.open_timeout_text,
                "Open timeout",
                MIN_OPEN_TIMEOUT_SECONDS,
                MAX_OPEN_TIMEOUT_SECONDS,
            )
            post_open_wait = self._parse_seconds(
                self.post_open_wait_text,
                "Wait after Roblox opens",
                MIN_POST_OPEN_WAIT_SECONDS,
                MAX_POST_OPEN_WAIT_SECONDS,
            )
        except ValueError as error:
            messagebox.showerror(APP_NAME, str(error))
            return
        if not self._apply_history_path():
            return
        if not self._apply_monitoring_sessions_path():
            return
        if not self.history_path.parent.is_dir():
            messagebox.showerror(
                APP_NAME,
                "The parent folder for the relaunch history file does not exist.",
            )
            return
        if not self.monitoring_sessions_path.parent.is_dir():
            messagebox.showerror(
                APP_NAME,
                "The parent folder for the monitoring sessions file does not exist.",
            )
            return
        self._save_settings()
        self.stop_event = threading.Event()
        replay_speed = float(self.replay_speed.get())
        self.worker = threading.Thread(
            target=self._monitor_loop,
            args=(self.stop_event, str(shortcut), replay_speed, open_timeout, post_open_wait),
            daemon=True,
        )
        try:
            self.worker.start()
        except RuntimeError as error:
            self.worker = None
            self.stop_event = None
            messagebox.showerror(
                APP_NAME, f"Could not start monitoring.\n\n{error}"
            )
            return
        self.monitor_session_started_at = datetime.now()
        self.monitor_session_started_monotonic = time.monotonic()
        self.stopwatch_text.set("Elapsed: 00:00:00")
        self._update_stopwatch()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.record_button.configure(state="disabled")
        self.replay_speed_scale.configure(state="disabled")
        for entry in self.monitor_setting_entries:
            entry.configure(state="disabled")
        self.sessions_path_entry.configure(state="disabled")
        self.sessions_browse_button.configure(state="disabled")
        self.clear_sessions_button.configure(state="disabled")
        self.status.set("Starting monitor...")

    def _stop_monitoring(self) -> None:
        if self.stop_event:
            self.stop_event.set()
        self.status.set("Stopping monitor...")
        self.stop_button.configure(state="disabled")

    def _post(self, kind: str, data: object) -> None:
        self.messages.put((kind, data))

    def _monitor_loop(
        self,
        stop_event: threading.Event,
        shortcut: str,
        replay_speed: float,
        open_timeout: int,
        post_open_wait: int,
    ) -> None:
        try:
            if roblox_is_running():
                self._post("status", "Monitoring: waiting for Roblox to close")
                waiting_for_open = False
            else:
                self._post("status", "Monitoring: waiting for Roblox to open")
                waiting_for_open = True

            while not stop_event.is_set():
                running = roblox_is_running()
                if waiting_for_open:
                    if running:
                        waiting_for_open = False
                        self._post("status", "Monitoring: waiting for Roblox to close")
                elif not running:
                    self._post("status", "Roblox closed; attempting relaunch")
                    success, reason = self._relaunch(
                        stop_event, shortcut, replay_speed, open_timeout, post_open_wait
                    )
                    if stop_event.is_set():
                        break
                    outcome = "SUCCESSFUL" if success else "FAILED"
                    now = datetime.now()
                    self._post(
                        "result",
                        {
                            "date": now.strftime("%Y/%m/%d"),
                            "time": now.strftime("%H:%M:%S"),
                            "timestamp": now.isoformat(timespec="seconds"),
                            "status": outcome,
                            "reason": reason,
                        },
                    )
                    if not success:
                        self._post("stopped", "Stopped after unsuccessful relaunch")
                        return
                    self._post("status", "Monitoring: waiting for Roblox to close")
                stop_event.wait(1.0)
        except Exception as error:
            self._post("error", f"Monitoring stopped because of an unexpected error:\n{error}")
            self._post("stopped", "Monitoring stopped after an error")
            return
        self._post("stopped", "Monitoring stopped")

    def _relaunch(
        self,
        stop_event: threading.Event,
        shortcut: str,
        replay_speed: float,
        open_timeout: int,
        post_open_wait: int,
    ) -> tuple[bool, str]:
        failures: list[str] = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if stop_event.is_set():
                return False, "Monitoring was stopped before the relaunch sequence finished."
            try:
                if not roblox_is_running():
                    os.startfile(shortcut)
                self._post(
                    "status", f"Relaunch attempt {attempt}/{MAX_ATTEMPTS}: waiting for Roblox"
                )
            except OSError as error:
                failures.append(f"Attempt {attempt}: could not open shortcut ({error}).")
                continue

            appeared_at = time.monotonic() if roblox_is_running() else None
            deadline = time.monotonic() + open_timeout
            while appeared_at is None and time.monotonic() < deadline:
                if stop_event.wait(0.5):
                    return False, "Monitoring was stopped during the relaunch."
                if roblox_is_running():
                    appeared_at = time.monotonic()
            if appeared_at is None:
                failures.append(
                    f"Attempt {attempt}: Roblox did not open within "
                    f"{open_timeout} seconds."
                )
                continue

            while time.monotonic() - appeared_at < post_open_wait:
                if stop_event.wait(0.2):
                    return False, (
                        f"Monitoring was stopped during the "
                        f"{post_open_wait}-second wait."
                    )
                if not roblox_is_running():
                    break
            if not roblox_is_running():
                failures.append(
                    f"Attempt {attempt}: Roblox closed before completing the "
                    f"{post_open_wait}-second wait."
                )
                continue

            try:
                self._replay_actions(stop_event, replay_speed)
            except (OSError, RuntimeError, ValueError) as error:
                failures.append(f"Attempt {attempt}: recorded actions could not be replayed ({error}).")
                continue
            click_count = sum(action.get("type") == "click" for action in self.macro)
            scroll_count = sum(action.get("type") == "scroll" for action in self.macro)
            move_count = sum(action.get("type") == "move" for action in self.macro)
            reason = (
                "Roblox Player was detected and remained open through the "
                f"{post_open_wait}-second wait. Replayed {move_count} "
                f"mouse path point(s), {click_count} click(s), and "
                f"{scroll_count} scroll event(s) at {replay_speed:.2f}x speed. "
                "The game launch itself was not verified."
            )
            return True, reason

        return False, (
            f"All {MAX_ATTEMPTS} attempts failed. "
            + " ".join(failures)
            + " Monitoring stopped."
        )

    def _replay_actions(
        self, stop_event: threading.Event, replay_speed: float
    ) -> None:
        if (
            not isinstance(replay_speed, (int, float))
            or not MIN_REPLAY_SPEED <= replay_speed <= MAX_REPLAY_SPEED
        ):
            raise ValueError(
                f"replay speed must be between {MIN_REPLAY_SPEED:.2f}x "
                f"and {MAX_REPLAY_SPEED:.2f}x."
            )
        hwnd = None
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not stop_event.is_set():
            hwnd = find_roblox_window()
            if hwnd:
                break
            stop_event.wait(0.25)
        if stop_event.is_set():
            raise RuntimeError("monitoring was stopped before replay.")
        if not hwnd:
            raise RuntimeError("Roblox opened, but its window was not found within 15 seconds.")
        if not self._focus_roblox_window(hwnd):
            raise RuntimeError("Roblox could not be brought to the foreground before replay.")
        focused_hwnd = hwnd

        for action in self.macro:
            if stop_event.is_set():
                raise RuntimeError("monitoring was stopped during action replay.")
            if not isinstance(action, dict):
                raise ValueError("the saved recording contains an invalid action.")
            delay = action.get("delay", 0)
            if not isinstance(delay, (int, float)) or delay < 0:
                raise ValueError("the saved recording contains an invalid action delay.")
            if stop_event.wait(min(delay, MAX_RECORDED_DELAY_SECONDS) / replay_speed):
                raise RuntimeError("monitoring was stopped during action replay.")

            hwnd = find_roblox_window()
            if not hwnd:
                raise RuntimeError("the Roblox window disappeared during action replay.")
            rect = client_screen_rect(hwnd)
            if not rect:
                raise RuntimeError("the Roblox window has no usable client area.")
            x_ratio = action.get("x")
            y_ratio = action.get("y")
            if (
                not isinstance(x_ratio, (int, float))
                or not isinstance(y_ratio, (int, float))
                or not 0 <= x_ratio <= 1
                or not 0 <= y_ratio <= 1
            ):
                raise ValueError("the saved recording contains an invalid position.")
            left, top, width, height = rect
            x = left + int(x_ratio * width)
            y = top + int(y_ratio * height)
            if hwnd != focused_hwnd or user32.GetForegroundWindow() != hwnd:
                if not self._focus_roblox_window(hwnd):
                    raise RuntimeError(
                        "Roblox could not be brought to the foreground; "
                        "remaining actions were not sent."
                    )
                focused_hwnd = hwnd
            if user32.GetForegroundWindow() != focused_hwnd:
                raise RuntimeError("Roblox lost focus; remaining actions were not sent.")
            self._send_mouse_input(
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                x=x,
                y=y,
            )
            if action.get("type") == "move":
                continue
            if action.get("type") == "scroll":
                delta = action.get("delta")
                if not isinstance(delta, int) or delta == 0:
                    raise ValueError("the saved recording contains an invalid scroll amount.")
                self._send_mouse_input(MOUSEEVENTF_WHEEL, data=delta & 0xFFFFFFFF)
            elif action.get("type") == "click":
                flags = {
                    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
                    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
                    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
                }.get(action.get("button"))
                if not flags:
                    raise ValueError("the saved recording contains an unsupported mouse button.")
                self._send_mouse_input(flags[0])
                if stop_event.wait(KEY_HOLD_SECONDS):
                    self._send_mouse_input(flags[1])
                    raise RuntimeError("monitoring was stopped during a click.")
                self._send_mouse_input(flags[1])
            else:
                raise ValueError("the saved recording contains an unknown action.")

    @staticmethod
    def _send_mouse_input(
        flags: int, data: int = 0, x: int = 0, y: int = 0
    ) -> None:
        if flags & MOUSEEVENTF_ABSOLUTE:
            left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            if width <= 1 or height <= 1:
                raise OSError("Windows did not report a usable virtual screen size.")
            dx = round((x - left) * 65535 / (width - 1))
            dy = round((y - top) * 65535 / (height - 1))
        else:
            dx = dy = 0

        input_event = INPUT()
        input_event.type = INPUT_MOUSE
        input_event.mi = MOUSEINPUT(
            dx,
            dy,
            data & 0xFFFFFFFF,
            flags,
            0,
            0,
        )
        sent = user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(INPUT))
        if sent != 1:
            raise ctypes.WinError()

    @staticmethod
    def _focus_roblox_window(hwnd: int) -> bool:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        current_thread = kernel32.GetCurrentThreadId()
        foreground_hwnd = user32.GetForegroundWindow()
        foreground_thread = (
            user32.GetWindowThreadProcessId(foreground_hwnd, None)
            if foreground_hwnd
            else 0
        )
        thread_pairs = {
            tuple(sorted((current_thread, target_thread))),
            tuple(sorted((current_thread, foreground_thread))),
            tuple(sorted((foreground_thread, target_thread))),
        }
        attached_pairs: list[tuple[int, int]] = []

        try:
            for first_thread, second_thread in thread_pairs:
                if (
                    first_thread
                    and second_thread
                    and first_thread != second_thread
                    and user32.AttachThreadInput(first_thread, second_thread, True)
                ):
                    attached_pairs.append((first_thread, second_thread))

            for _ in range(10):
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
                user32.SetActiveWindow(hwnd)
                user32.SetFocus(hwnd)
                if user32.GetForegroundWindow() == hwnd:
                    return True
                time.sleep(0.1)
            return False
        finally:
            for first_thread, second_thread in reversed(attached_pairs):
                user32.AttachThreadInput(first_thread, second_thread, False)

    def _process_messages(self) -> None:
        while True:
            try:
                kind, data = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.status.set(str(data))
            elif kind == "result":
                self._add_history(data)
            elif kind == "stopped":
                self.status.set(str(data))
                self._finish_monitoring_session()
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                self.record_button.configure(state="normal")
                self.replay_speed_scale.configure(state="normal")
                for entry in self.monitor_setting_entries:
                    entry.configure(state="normal")
                self.sessions_path_entry.configure(state="normal")
                self.sessions_browse_button.configure(state="normal")
                self.clear_sessions_button.configure(state="normal")
            elif kind == "error":
                messagebox.showerror(APP_NAME, str(data))
            elif kind == "recording_error":
                messagebox.showerror(
                    APP_NAME, f"Could not record a Roblox mouse action:\n\n{data}"
                )
        self.root.after(100, self._process_messages)

    def _insert_history_row(self, entry: dict) -> None:
        status = entry.get("status", "FAILED")
        self.log.insert(
            "end",
            f"{entry.get('date', '')}  ·  {entry.get('time', '')}  ",
            "META",
        )
        self.log.insert("end", status, status)
        self.log.insert("end", "\n", "META")
        self.log.insert("end", str(entry.get("reason", "")), "REASON")
        self.log.insert("end", "\n\n")

    def _add_history(self, entry: dict) -> None:
        self.history.insert(0, entry)
        self._render_history()
        try:
            write_json(self.history_path, self.history)
        except OSError as error:
            messagebox.showerror(
                APP_NAME,
                f"The result is visible, but its history could not be saved to:\n"
                f"{self.history_path}\n\n{error}",
            )

    @staticmethod
    def _format_elapsed_time(seconds: float) -> str:
        elapsed = max(0, int(seconds))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds_part = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"

    def _update_stopwatch(self) -> None:
        started = self.monitor_session_started_monotonic
        if started is None:
            self.stopwatch_text.set("Elapsed: 00:00:00")
            self.stopwatch_after = None
            return
        self.stopwatch_text.set(
            f"Elapsed: {self._format_elapsed_time(time.monotonic() - started)}"
        )
        self.stopwatch_after = self.root.after(250, self._update_stopwatch)

    def _finish_monitoring_session(self) -> None:
        started_at = self.monitor_session_started_at
        started_monotonic = self.monitor_session_started_monotonic
        if started_at is None or started_monotonic is None:
            return
        if self.stopwatch_after is not None:
            self.root.after_cancel(self.stopwatch_after)
            self.stopwatch_after = None
        ended_at = datetime.now()
        elapsed_seconds = max(0, int(time.monotonic() - started_monotonic))
        entry = {
            "date": started_at.strftime("%Y/%m/%d"),
            "time_started": started_at.strftime("%H:%M:%S"),
            "time_ended": ended_at.strftime("%H:%M:%S"),
            "elapsed_time": self._format_elapsed_time(elapsed_seconds),
            "elapsed_seconds": elapsed_seconds,
            "started_at": started_at.isoformat(timespec="seconds"),
            "ended_at": ended_at.isoformat(timespec="seconds"),
        }
        self.monitor_session_started_at = None
        self.monitor_session_started_monotonic = None
        self.stopwatch_text.set("Elapsed: 00:00:00")
        self.monitoring_sessions.insert(0, entry)
        self._render_monitoring_sessions()
        try:
            write_json(self.monitoring_sessions_path, self.monitoring_sessions)
        except OSError as error:
            messagebox.showerror(
                APP_NAME,
                "The monitoring session is visible, but could not be saved to:\n"
                f"{self.monitoring_sessions_path}\n\n{error}",
            )

    def _load_monitoring_sessions(self) -> None:
        if not self.monitoring_sessions_path.exists():
            return
        try:
            data = json.loads(
                self.monitoring_sessions_path.read_text(encoding="utf-8")
            )
            if not isinstance(data, list):
                raise ValueError("The monitoring sessions file must contain a JSON list.")
            required_fields = (
                "date",
                "time_started",
                "time_ended",
                "elapsed_time",
            )
            if any(
                not isinstance(entry, dict)
                or any(not isinstance(entry.get(field), str) for field in required_fields)
                for entry in data
            ):
                raise ValueError("The monitoring sessions file contains an invalid entry.")
            self.monitoring_sessions = data
            self._render_monitoring_sessions()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            messagebox.showwarning(
                APP_NAME,
                "Monitoring sessions could not be loaded from:\n"
                f"{self.monitoring_sessions_path}\n\n{error}",
            )

    def _render_monitoring_sessions(self) -> None:
        if not hasattr(self, "sessions_table"):
            return
        for item in self.sessions_table.get_children():
            self.sessions_table.delete(item)
        for entry in self.monitoring_sessions:
            self.sessions_table.insert(
                "",
                "end",
                values=(
                    entry.get("date", ""),
                    entry.get("time_started", ""),
                    entry.get("time_ended", ""),
                    entry.get("elapsed_time", ""),
                ),
            )

    def _render_history(self) -> None:
        if not hasattr(self, "log"):
            return
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        if not self.history:
            self.log.insert("end", "No relaunch activity yet.", "EMPTY")
        else:
            for entry in self.history:
                self._insert_history_row(entry)
        self.log.configure(state="disabled")
        self.log.yview_moveto(0)

    def _layout_history_body(self, _event=None) -> None:
        if not hasattr(self, "history_body"):
            return
        top = (
            self.history_location.winfo_y()
            + self.history_location.winfo_height()
            + 10
        )
        self.history_body.place_configure(
            x=14,
            y=top,
            width=max(1, self.history_panel.winfo_width() - 28),
            height=max(1, self.history_panel.winfo_height() - top - 14),
        )

    @staticmethod
    def _history_entry_datetime(entry: dict) -> datetime | None:
        value = entry.get("timestamp")
        parsed: datetime | None = None
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                parsed = None
        if parsed is None:
            try:
                parsed = datetime.strptime(
                    f"{entry.get('date', '')} {entry.get('time', '')}",
                    "%Y/%m/%d %H:%M:%S",
                )
            except (TypeError, ValueError):
                return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed

    def _open_clear_history_dialog(self) -> None:
        self._open_clear_log_dialog(
            "Relaunch history", self._confirm_clear_history
        )

    def _open_clear_sessions_dialog(self) -> None:
        self._open_clear_log_dialog(
            "Monitoring Sessions", self._confirm_clear_monitoring_sessions
        )

    def _open_clear_log_dialog(
        self,
        log_name: str,
        confirm_command: Callable[[tk.Toplevel, str], None],
    ) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Clear {log_name}")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(background=self.colors["background"])
        dialog.grab_set()
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content, text="Choose how much history to remove", style="Section.TLabel"
        ).pack(anchor="w", pady=(0, 12))
        selection = tk.StringVar(value="all")
        options = (
            ("All time", "all"),
            ("Last hour", "hour"),
            ("Last 24 hours", "day"),
            ("Last 7 days", "week"),
            ("Last 30 days", "month"),
        )
        for label, value in options:
            ttk.Radiobutton(
                content, text=label, variable=selection, value=value
            ).pack(anchor="w", pady=2)
        actions = ttk.Frame(content)
        actions.pack(fill="x", pady=(16, 0))
        ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(
            actions,
            text="Continue",
            style="Primary.TButton",
            command=lambda: confirm_command(dialog, selection.get()),
        ).pack(side="right", padx=(0, 8))
        dialog.update_idletasks()
        dialog.geometry(
            f"+{self.root.winfo_rootx() + 180}+{self.root.winfo_rooty() + 120}"
        )

    def _confirm_clear_history(self, dialog: tk.Toplevel, period: str) -> None:
        self._confirm_clear_log(
            dialog,
            period,
            "Relaunch history",
            self.history,
            self.history_path,
            self._history_entry_datetime,
            self._replace_history,
        )

    def _confirm_clear_monitoring_sessions(
        self, dialog: tk.Toplevel, period: str
    ) -> None:
        self._confirm_clear_log(
            dialog,
            period,
            "Monitoring Sessions",
            self.monitoring_sessions,
            self.monitoring_sessions_path,
            self._monitoring_session_datetime,
            self._replace_monitoring_sessions,
        )

    def _confirm_clear_log(
        self,
        dialog: tk.Toplevel,
        period: str,
        log_name: str,
        entries: list[dict],
        path: Path,
        datetime_getter: Callable[[dict], datetime | None],
        replace_entries: Callable[[list[dict]], None],
    ) -> None:
        dialog.destroy()
        period_names = {
            "all": "all time",
            "hour": "the last hour",
            "day": "the last 24 hours",
            "week": "the last 7 days",
            "month": "the last 30 days",
        }
        if not messagebox.askyesno(
            APP_NAME,
            f"Delete {log_name} from {period_names[period]}?",
            icon="warning",
        ):
            return
        durations = {
            "hour": timedelta(hours=1),
            "day": timedelta(days=1),
            "week": timedelta(days=7),
            "month": timedelta(days=30),
        }
        if period == "all":
            remaining = []
        else:
            cutoff = datetime.now() - durations[period]
            remaining = []
            for entry in entries:
                entry_time = datetime_getter(entry)
                if entry_time is None or entry_time < cutoff:
                    remaining.append(entry)
        removed_count = len(entries) - len(remaining)
        if not removed_count:
            messagebox.showinfo(APP_NAME, f"There are no matching {log_name} entries.")
            return
        try:
            write_json(path, remaining)
        except OSError as error:
            messagebox.showerror(
                APP_NAME,
                f"{log_name} could not be cleared from:\n{path}\n\n{error}",
            )
            return
        replace_entries(remaining)
        messagebox.showinfo(
            APP_NAME,
            f"Deleted {removed_count} {log_name} "
            f"{'entry' if removed_count == 1 else 'entries'}.",
        )

    def _replace_history(self, entries: list[dict]) -> None:
        self.history = entries
        self._render_history()

    def _replace_monitoring_sessions(self, entries: list[dict]) -> None:
        self.monitoring_sessions = entries
        self._render_monitoring_sessions()

    @staticmethod
    def _monitoring_session_datetime(entry: dict) -> datetime | None:
        started_at = entry.get("started_at")
        if isinstance(started_at, str):
            try:
                parsed = datetime.fromisoformat(started_at)
            except ValueError:
                parsed = None
            else:
                if parsed.tzinfo is not None:
                    return parsed.astimezone().replace(tzinfo=None)
                return parsed
        try:
            return datetime.strptime(
                f"{entry.get('date', '')} {entry.get('time_started', '')}",
                "%Y/%m/%d %H:%M:%S",
            )
        except (TypeError, ValueError):
            return None

    def _close(self) -> None:
        if self.recorder.recording:
            try:
                self.recorder.stop()
            except OSError as error:
                messagebox.showerror(APP_NAME, f"Could not stop the recorder.\n\n{error}")
        self._save_settings()
        if self.stop_event:
            self.stop_event.set()
        self._finish_monitoring_session()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        RobloxRecoveryApp(root)
    except OSError as error:
        messagebox.showerror(APP_NAME, f"Could not initialize the application.\n\n{error}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
