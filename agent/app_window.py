"""
app_window.py — Complete tkinter UI for the Device Security Agent.

Two screens managed inside a single Tk() root:
  • LoginScreen   — registration form + Zoho OAuth connect button
  • Dashboard     — compliance score, security checks, Send Evidence, countdown

Thread-safety rule: all root.* / widget.* calls MUST happen on the main thread.
Background work posts back via root.after(0, callback).
"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageTk

from . import config

logger = logging.getLogger(__name__)

# ─── Brand Colours (Industrility: black + gold + white) ─────────────────────
BG          = "#1A1A1A"      # near-black background
BG_CARD     = "#242424"      # card surface
BG_INPUT    = "#2E2E2E"      # input field background
BG_HEADER   = "#111111"      # top header strip
GOLD        = "#F5C518"      # Industrility gold
GOLD_DARK   = "#C9A000"      # darker gold for hover
WHITE       = "#FFFFFF"
GREY        = "#AAAAAA"
GREY_DIM    = "#666666"
GREEN       = "#2ECC71"
RED         = "#E74C3C"
AMBER       = "#F39C12"
BORDER      = "#333333"

# ─── Fonts ────────────────────────────────────────────────────────────────────
_WIN  = sys.platform == "win32"
_MAC  = sys.platform == "darwin"

def F(size, weight="normal"):
    family = "Segoe UI" if _WIN else ("-apple-system" if _MAC else "DejaVu Sans")
    return (family, size, weight)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _asset(filename: str) -> str:
    """Return absolute path to an asset file (works inside PyInstaller bundle)."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent
    return os.path.join(base, "assets", filename)


def _load_logo(size: tuple[int, int] = (340, 95)) -> Optional[ImageTk.PhotoImage]:
    """Load and resize the high-resolution Industriility logo cleanly."""
    try:
        path = _asset("logo_header_clean.png")
        if not os.path.exists(path):
            path = _asset("logo_production_brand.png")
        img = Image.open(path).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        logger.warning(f"Could not load logo: {e}")
        return None


def _next_friday() -> str:
    """Return human-readable string for the next Friday 08:00."""
    now = datetime.now()
    days_ahead = (4 - now.weekday()) % 7  # Friday = weekday 4
    if days_ahead == 0 and now.hour >= config.SCAN_HOUR:
        days_ahead = 7
    nf = now + timedelta(days=days_ahead)
    nf = nf.replace(hour=config.SCAN_HOUR, minute=0, second=0, microsecond=0)
    return nf.strftime("%A %d %b at %H:%M")


# ─── Reusable Widgets ─────────────────────────────────────────────────────────

class GoldButton(tk.Button):
    """A gold-accented CTA button."""
    def __init__(self, parent, text, command, large=False, **kwargs):
        size = 13 if large else 11
        super().__init__(
            parent,
            text=text,
            command=command,
            font=F(size, "bold"),
            bg=GOLD, fg="#000000",
            activebackground=GOLD_DARK,
            activeforeground="#000000",
            relief="flat", bd=0,
            cursor="hand2",
            padx=24 if large else 16,
            pady=12 if large else 8,
            **kwargs,
        )

    def set_loading(self, loading: bool, text_on: str, text_off: str):
        self.config(
            text=text_on if loading else text_off,
            state="disabled" if loading else "normal",
            bg=GOLD_DARK if loading else GOLD,
        )


class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent, text=text.upper(),
            font=F(9, "bold"), bg=BG, fg=GREY_DIM,
            anchor="w", **kwargs,
        )


class EntryField(tk.Frame):
    """Dark-styled labelled entry."""
    def __init__(self, parent, label: str, placeholder: str = "", password: bool = False):
        super().__init__(parent, bg=BG)
        tk.Label(self, text=label, font=F(10), bg=BG, fg=GREY, anchor="w").pack(fill="x")
        self.var = tk.StringVar()
        show = "*" if password else ""
        self.entry = tk.Entry(
            self, textvariable=self.var,
            font=F(12), bg=BG_INPUT, fg=WHITE,
            insertbackground=WHITE, relief="flat", bd=0,
            show=show,
            highlightthickness=1,
            highlightcolor=GOLD,
            highlightbackground=BORDER,
        )
        self.entry.pack(fill="x", ipady=9)
        self._ph = placeholder
        self._ph_active = False
        if placeholder:
            self._set_placeholder()
        self.entry.bind("<FocusIn>",  self._clear_ph)
        self.entry.bind("<FocusOut>", self._set_ph_if_empty)
        self.err = tk.Label(self, text="", font=F(9), bg=BG, fg=RED, anchor="w")
        self.err.pack(fill="x")

    def _set_placeholder(self):
        self.entry.insert(0, self._ph)
        self.entry.config(fg=GREY_DIM)
        self._ph_active = True

    def _clear_ph(self, _=None):
        if self._ph_active:
            self.entry.delete(0, "end")
            self.entry.config(fg=WHITE)
            self._ph_active = False

    def _set_ph_if_empty(self, _=None):
        if not self.entry.get().strip() and not self._ph_active:
            self._set_placeholder()

    def get(self) -> str:
        v = self.var.get().strip()
        return "" if v == self._ph else v

    def set_error(self, msg: str):
        self.err.config(text=msg)
        self.entry.config(highlightbackground=RED)

    def clear_error(self):
        self.err.config(text="")
        self.entry.config(highlightbackground=BORDER)


# ─── Login / Registration Screen ─────────────────────────────────────────────

class LoginScreen(tk.Frame):
    """
    Shown on first launch or when not authenticated.
    Collects employee info, then triggers Zoho OAuth.
    """
    def __init__(self, parent, on_login_success: Callable[[dict], None]):
        super().__init__(parent, bg=BG)
        self.on_login_success = on_login_success
        self._logo_img = None
        self._build()

    def _build(self):
        # Scrollable canvas for short screens
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _on_resize)

        def _update_scroll(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _update_scroll)

        self._build_inner(inner)

    def _build_inner(self, p):
        # Header
        hdr = tk.Frame(p, bg=BG_HEADER)
        hdr.pack(fill="x")
        self._logo_img = _load_logo((360, 108))
        if self._logo_img:
            tk.Label(hdr, image=self._logo_img, bg=BG_HEADER).pack(pady=(16, 12))
        else:
            tk.Label(hdr, text="INDUSTRILITY", font=F(22, "bold"),
                     bg=BG_HEADER, fg=GOLD).pack(pady=(16, 4))
            tk.Label(hdr, text="DEVICE SECURITY MONITOR",
                     font=F(11, "bold"), bg=BG_HEADER, fg=WHITE).pack(pady=(0, 12))

        # Gold divider
        tk.Frame(p, bg=GOLD, height=2).pack(fill="x")

        # Card
        card = tk.Frame(p, bg=BG_CARD)
        card.pack(fill="x", padx=32, pady=20)

        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="both", padx=28, pady=20)

        SectionLabel(inner, "Industrility Employee Login").pack(fill="x", pady=(0, 12))

        self.f_name  = EntryField(inner, "Full Name",            "e.g. Kavy Vachhani")
        self.f_email = EntryField(inner, "Industrility Email",  "user@industrility.com")
        self.f_pass  = EntryField(inner, "Password",             "••••••••", password=True)
        self.f_dept  = EntryField(inner, "Department",           "e.g. Engineering")

        for field in [self.f_name, self.f_email, self.f_pass, self.f_dept]:
            field.pack(fill="x", pady=(0, 8))

        # Status label
        self.status_lbl = tk.Label(inner, text="", font=F(10), bg=BG_CARD, fg=GREY, wraplength=380)
        self.status_lbl.pack(pady=(4, 10))

        # CTA Button
        self.btn = GoldButton(
            inner, "🔐   Sign In & Connect Device",
            command=self._submit, large=True,
        )
        self.btn.pack(fill="x")

        tk.Label(p, text="🔒  Evidence will be saved to your employee folder on Zoho WorkDrive",
                 font=F(9), bg=BG, fg=GREY_DIM).pack(pady=(8, 24))

    def _submit(self):
        # Validate
        errors = False
        import re
        def check(field, cond, msg):
            nonlocal errors
            if not cond:
                field.set_error(msg); errors = True
            else:
                field.clear_error()

        check(self.f_name,  len(self.f_name.get()) >= 2,                      "Enter your full name")
        check(self.f_email, bool(re.match(r"[^@]+@[^@]+\.[^@]+",
                                          self.f_email.get())),                "Enter a valid work email")
        check(self.f_pass,  len(self.f_pass.get()) >= 4,                      "Enter your password")
        check(self.f_dept,  len(self.f_dept.get()) >= 2,                      "Enter your department")

        if errors:
            return

        profile = {
            "full_name":   self.f_name.get(),
            "work_email":  self.f_email.get(),
            "department":  self.f_dept.get(),
            "employee_id": self.f_email.get().split('@')[0].upper(),
        }

        from . import registration
        registration._save_profile(profile)
        self.on_login_success(profile)

    def _login_error(self, msg: str):
        self.btn.set_loading(False, "", "🔐  Connect with Zoho WorkDrive")
        self.status_lbl.config(text=f"Login failed: {msg}", fg=RED)


# ─── Dashboard Screen ─────────────────────────────────────────────────────────

class Dashboard(tk.Frame):
    """
    Main screen after successful Zoho login.
    Shows compliance score, per-check details, Send Evidence button, countdown.
    """
    def __init__(self, parent, profile: dict, on_logout: Callable):
        super().__init__(parent, bg=BG)
        self.profile    = profile
        self.on_logout  = on_logout
        self._logo_img  = None
        self._check_rows: dict[str, tk.Label] = {}     # key → status dot label
        self._check_detail: dict[str, tk.Label] = {}   # key → detail label
        self._scan_running = False
        self._build()
        self._start_countdown()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Top header bar ─────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_HEADER)
        hdr.pack(fill="x")

        left = tk.Frame(hdr, bg=BG_HEADER)
        left.pack(side="left", padx=16, pady=8)
        self._logo_img = _load_logo((240, 52))
        if self._logo_img:
            tk.Label(left, image=self._logo_img, bg=BG_HEADER).pack(side="left")
        else:
            tk.Label(left, text="INDUSTRIILITY AGENT", font=F(12, "bold"),
                     bg=BG_HEADER, fg=GOLD).pack(side="left")

        right = tk.Frame(hdr, bg=BG_HEADER)
        right.pack(side="right", padx=16)
        self.emp_lbl = tk.Label(
            right,
            text=f"👤  {self.profile.get('full_name','Employee')}",
            font=F(10), bg=BG_HEADER, fg=GREY,
        )
        self.emp_lbl.pack(side="right")

        # Gold divider
        tk.Frame(self, bg=GOLD, height=2).pack(fill="x")

        # Scrollable body
        body_canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        vbar = tk.Scrollbar(self, orient="vertical", command=body_canvas.yview)
        body_canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        body_canvas.pack(side="left", fill="both", expand=True)

        self._body = tk.Frame(body_canvas, bg=BG)
        body_win = body_canvas.create_window((0, 0), window=self._body, anchor="nw")

        def _resize(e):
            body_canvas.itemconfig(body_win, width=e.width)
        body_canvas.bind("<Configure>", _resize)

        def _scroll_update(e):
            body_canvas.configure(scrollregion=body_canvas.bbox("all"))
        self._body.bind("<Configure>", _scroll_update)

        self._build_body(self._body)

    def _build_body(self, p):
        pad = {"padx": 24, "pady": 8}

        # ── Compliance Score Card ──────────────────────────────────────────────
        score_card = tk.Frame(p, bg=BG_CARD, relief="flat")
        score_card.pack(fill="x", **pad)
        inner = tk.Frame(score_card, bg=BG_CARD)
        inner.pack(padx=24, pady=20)

        SectionLabel(inner, "Compliance Score").pack(fill="x")

        bar_frame = tk.Frame(inner, bg=BG_CARD)
        bar_frame.pack(fill="x", pady=(8, 4))

        self.score_lbl = tk.Label(bar_frame, text="—", font=F(36, "bold"),
                                  bg=BG_CARD, fg=GOLD)
        self.score_lbl.pack(side="left")

        right_side = tk.Frame(bar_frame, bg=BG_CARD)
        right_side.pack(side="left", padx=20, fill="x", expand=True)

        # Progress bar (canvas)
        self.progress_canvas = tk.Canvas(right_side, height=16, bg=BORDER,
                                         highlightthickness=0, relief="flat")
        self.progress_canvas.pack(fill="x", pady=(8, 4))
        self.overall_lbl = tk.Label(right_side, text="No scan yet",
                                    font=F(11, "bold"), bg=BG_CARD, fg=GREY)
        self.overall_lbl.pack(anchor="w")

        self.scan_ts_lbl = tk.Label(inner, text="Last scan: Never",
                                    font=F(9), bg=BG_CARD, fg=GREY_DIM)
        self.scan_ts_lbl.pack(anchor="w", pady=(4, 0))

        # ── Security Checks ────────────────────────────────────────────────────
        checks_card = tk.Frame(p, bg=BG_CARD)
        checks_card.pack(fill="x", **pad)
        checks_inner = tk.Frame(checks_card, bg=BG_CARD)
        checks_inner.pack(fill="x", padx=24, pady=20)

        SectionLabel(checks_inner, "Security Checks").pack(fill="x", pady=(0, 10))

        check_keys = [
            ("disk_encryption", "Disk Encryption"),
            ("firewall",        "Firewall"),
            ("screen_lock",     "Screen Lock"),
            ("os_patch",        "OS Updates"),
            ("antivirus",       "Antivirus"),
            ("secure_boot",     "Secure Boot / SIP"),
            ("password_policy", "Password Policy"),
        ]
        for i, (key, label) in enumerate(check_keys):
            row = tk.Frame(checks_inner, bg=BG_CARD if i % 2 == 0 else BG)
            row.pack(fill="x", pady=1)
            dot = tk.Label(row, text="●", font=F(14), bg=row["bg"], fg=GREY_DIM, width=2)
            dot.pack(side="left", padx=(4, 8), pady=6)
            tk.Label(row, text=label, font=F(11, "bold"),
                     bg=row["bg"], fg=WHITE, width=18, anchor="w").pack(side="left")
            detail = tk.Label(row, text="—", font=F(10), bg=row["bg"],
                              fg=GREY, anchor="w", wraplength=300)
            detail.pack(side="left", fill="x", expand=True)
            self._check_rows[key]   = dot
            self._check_detail[key] = detail

        # ── Action Buttons ─────────────────────────────────────────────────────
        btn_card = tk.Frame(p, bg=BG_CARD)
        btn_card.pack(fill="x", **pad)
        btn_inner = tk.Frame(btn_card, bg=BG_CARD)
        btn_inner.pack(fill="x", padx=24, pady=20)

        self.send_btn = GoldButton(
            btn_inner,
            "📤   Send Evidence to Zoho WorkDrive",
            command=self._send_now,
            large=True,
        )
        self.send_btn.pack(fill="x")

        self.upload_status = tk.Label(btn_inner, text="", font=F(10),
                                      bg=BG_CARD, fg=GREY, wraplength=450)
        self.upload_status.pack(pady=(8, 0))

        # ── Info Footer ────────────────────────────────────────────────────────
        info = tk.Frame(p, bg=BG)
        info.pack(fill="x", padx=24, pady=8)

        self.countdown_lbl = tk.Label(
            info, text="", font=F(10), bg=BG, fg=GREY, anchor="w",
        )
        self.countdown_lbl.pack(side="left")

        logout_btn = tk.Button(
            info, text="🚪  Sign Out", font=F(10, "bold"),
            bg=BG, fg=RED, activebackground=BG, activeforeground="#FF6B6B",
            relief="flat", bd=0, cursor="hand2", command=self.on_logout,
        )
        logout_btn.pack(side="right")

        tk.Frame(p, bg=BG, height=20).pack()  # bottom padding

        # Load last report if exists
        self._load_existing_report()

    # ── Data / Scan ────────────────────────────────────────────────────────────

    def _load_existing_report(self):
        if os.path.exists(config.LAST_REPORT_FILE):
            try:
                with open(config.LAST_REPORT_FILE) as f:
                    report = json.load(f)
                self._apply_report(report, uploaded=False)
            except Exception:
                pass

    def _prompt_grant_token(self):
        top = tk.Toplevel(self)
        top.title("Connect to Zoho WorkDrive")
        top.configure(bg=BG)
        top.geometry("460x270")
        top.resizable(False, False)

        tk.Label(top, text="🔐 Zoho WorkDrive Authentication", font=F(12, "bold"), bg=BG, fg=GOLD).pack(pady=(16, 8))
        tk.Label(top, text="Enter your Zoho Self Client Grant Token\n(Generated from api-console.zoho.com → Generate Code):",
                 font=F(10), bg=BG, fg=WHITE, justify="center").pack(pady=(0, 10))

        entry_var = tk.StringVar()
        entry = tk.Entry(top, textvariable=entry_var, font=F(10), bg=BG_INPUT, fg=WHITE, insertbackground=WHITE, width=42)
        entry.pack(pady=6, ipady=4)
        entry.focus()

        err_lbl = tk.Label(top, text="", font=F(9), bg=BG, fg=RED)
        err_lbl.pack(pady=2)

        def _do_auth():
            gt = entry_var.get().strip()
            if not gt:
                err_lbl.config(text="Please enter a valid grant token")
                return
            try:
                from . import auth
                auth.authenticate_with_grant_token(gt)
                top.destroy()
                self._send_now()
            except Exception as ex:
                err_lbl.config(text=f"Auth failed: {ex}")

        tk.Button(top, text="Save & Connect", command=_do_auth, bg=GOLD, fg="#111111", font=F(10, "bold"), relief="flat", padx=16, pady=6).pack(pady=10)

    def _send_now(self):
        if self._scan_running:
            return
        from . import auth
        if not auth.is_authenticated():
            self._prompt_grant_token()
            return

        self._scan_running = True
        self.send_btn.set_loading(True,
                                  "⏳  Scanning device & uploading...",
                                  "📤   Send Evidence to Zoho WorkDrive")
        self.upload_status.config(text="Running security checks...", fg=GOLD)

        def _worker():
            from . import collector, uploader
            try:
                report = collector.collect(self.profile)
                collector.save_report_locally(report)
                self.after(0, lambda r=report: self._apply_report(r, uploaded=False))
                self.after(0, lambda: self.upload_status.config(
                    text="Uploading to Zoho WorkDrive...", fg=GOLD))
                try:
                    url = uploader.upload_evidence(report)
                    self.after(0, lambda u=url: self._upload_done(True, u))
                except Exception as e:
                    self.after(0, lambda err=str(e): self._upload_done(False, err))
            except Exception as e:
                self.after(0, lambda err=str(e): self._scan_error(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_report(self, report: dict, uploaded: bool):
        """Update all UI elements from a report dict (must be called on main thread)."""
        score   = report.get("compliance_score", 0)
        overall = report.get("overall_status", "UNKNOWN")
        ts      = report.get("scan_timestamp", "")
        checks  = report.get("checks", {})

        # Score label
        score_colour = GREEN if overall == "PASS" else (AMBER if score >= 50 else RED)
        self.score_lbl.config(text=f"{score}%", fg=score_colour)

        # Progress bar
        self.progress_canvas.update_idletasks()
        w = self.progress_canvas.winfo_width()
        self.progress_canvas.delete("all")
        self.progress_canvas.create_rectangle(0, 0, w, 16, fill=BORDER, outline="")
        filled = int(w * score / 100)
        if filled > 0:
            self.progress_canvas.create_rectangle(0, 0, filled, 16,
                                                   fill=score_colour, outline="")

        # Overall badge
        badge = "✅  PASS" if overall == "PASS" else "❌  FAIL"
        self.overall_lbl.config(text=badge, fg=score_colour)

        # Timestamp
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            ts_str = dt.strftime("%d %b %Y  %H:%M UTC")
        except Exception:
            ts_str = ts[:16].replace("T", " ") if ts else "—"
        self.scan_ts_lbl.config(text=f"Last scan: {ts_str}")

        # Check rows
        colours = {"compliant": GREEN, "non_compliant": RED, "unknown": AMBER}
        for key, dot_lbl in self._check_rows.items():
            result = checks.get(key, {})
            st     = result.get("status", "unknown")
            detail = result.get("detail", "—")
            dot_lbl.config(fg=colours.get(st, GREY_DIM))
            self._check_detail[key].config(text=detail)

    def _upload_done(self, success: bool, msg: str):
        self._scan_running = False
        self.send_btn.set_loading(False, "", "📤   Send Evidence to Zoho WorkDrive")
        if success:
            self.upload_status.config(
                text=f"✅  Uploaded successfully → {msg}", fg=GREEN)
        else:
            self.upload_status.config(
                text=f"❌  Upload failed: {msg}", fg=RED)

    def _scan_error(self, msg: str):
        self._scan_running = False
        self.send_btn.set_loading(False, "", "📤   Send Evidence to Zoho WorkDrive")
        self.upload_status.config(text=f"❌  Scan error: {msg}", fg=RED)

    # ── Countdown Timer ────────────────────────────────────────────────────────

    def _start_countdown(self):
        self._update_countdown()

    def _update_countdown(self):
        nf = _next_friday()
        self.countdown_lbl.config(text=f"⏰  Next auto-scan: {nf}")
        # Refresh every 60 seconds
        self.after(60_000, self._update_countdown)


# ─── Main Application Window ──────────────────────────────────────────────────

class DeviceSecurityApp:
    """
    Top-level application.
    Manages a single Tk() root and swaps Login / Dashboard frames.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Industrility — Device Security Agent")
        self.root.configure(bg=BG)
        self.root.geometry("620x760")
        self.root.minsize(560, 600)
        self._current_frame: Optional[tk.Frame] = None
        self._scheduler_started = False
        self._scheduler = None
        self._set_window_icon()

    def _set_window_icon(self):
        try:
            path = _asset("icon_master.png")
            if not os.path.exists(path):
                path = _asset("Industirlity.png")
            img = Image.open(path).convert("RGBA").resize((64, 64), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, photo)
            self.root._icon_photo = photo  # prevent GC
        except Exception:
            pass

    def _show(self, frame: tk.Frame):
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = frame
        frame.pack(fill="both", expand=True)

    def _on_login_success(self, profile: dict):
        self._start_scheduler(profile)
        dash = Dashboard(self.root, profile, on_logout=self._logout)
        self._show(dash)

    def _logout(self):
        from . import auth
        auth.clear_tokens()
        if self._scheduler:
            try:
                self._scheduler.stop()
            except Exception:
                pass
            self._scheduler = None
        self._scheduler_started = False

        if os.path.exists(config.PROFILE_FILE):
            try:
                os.remove(config.PROFILE_FILE)
            except Exception:
                pass
        if os.path.exists(config.LAST_REPORT_FILE):
            try:
                os.remove(config.LAST_REPORT_FILE)
            except Exception:
                pass
        login = LoginScreen(self.root, on_login_success=self._on_login_success)
        self._show(login)

    def _start_scheduler(self, profile: dict):
        if self._scheduler_started:
            return
        self._scheduler_started = True
        from .scheduler import ScanScheduler
        from . import collector, uploader

        def _auto_scan():
            try:
                report = collector.collect(profile)
                collector.save_report_locally(report)
                uploader.upload_evidence(report)
                logger.info("Auto-scan complete.")
            except Exception as e:
                logger.error(f"Auto-scan error: {e}", exc_info=True)

        self._scheduler = ScanScheduler(scan_fn=_auto_scan)
        self._scheduler.start()
        logger.info(f"Scheduler started. Next: {self._scheduler.next_run_time()}")

    def start(self):
        """Decide which screen to show, then enter the main loop."""
        from . import auth, registration

        profile = registration.load_profile()

        if profile and auth.is_authenticated():
            # Straight to dashboard
            self._start_scheduler(profile)
            dash = Dashboard(self.root, profile, on_logout=self._logout)
            self._show(dash)
        else:
            # Show login / registration
            login = LoginScreen(self.root, on_login_success=self._on_login_success)
            self._show(login)

        # macOS: keep process alive when window is closed (hide instead of quit)
        if _MAC:
            self.root.protocol("WM_DELETE_WINDOW", self._hide_window)
        else:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.mainloop()

    def _hide_window(self):
        """macOS: hide to Dock (keep scheduler running)."""
        self.root.withdraw()

    def _on_close(self):
        if self._scheduler:
            self._scheduler.stop()
        self.root.destroy()


def launch():
    app = DeviceSecurityApp()
    app.start()
