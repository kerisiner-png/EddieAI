import tkinter as tk
from datetime import datetime


class ChatWindow:

    def __init__(self):
        self._root = tk.Toplevel()
        self._root.title("EddieAI Chat")
        self._root.geometry("500x600")
        self._root.minsize(300, 400)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._send_callback = None
        self._build_ui()

    def _build_ui(self):
        msg_frame = tk.Frame(self._root)
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 0))

        self._text = tk.Text(
            msg_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=8,
            pady=4,
        )
        scrollbar = tk.Scrollbar(
            msg_frame, command=self._text.yview
        )
        self._text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._text.tag_configure(
            "ai",
            background="SystemButtonFace",
            justify="left",
            lmargin1=4,
            lmargin2=4,
            rmargin=60,
        )
        self._text.tag_configure(
            "ai_ts",
            font=("TkDefaultFont", 8),
            foreground="gray",
            justify="left",
        )
        self._text.tag_configure(
            "user",
            background="#D6EAF8",
            justify="right",
            lmargin1=60,
            lmargin2=4,
            rmargin=4,
        )
        self._text.tag_configure(
            "user_ts",
            font=("TkDefaultFont", 8),
            foreground="gray",
            justify="right",
        )

        input_frame = tk.Frame(self._root)
        input_frame.pack(fill=tk.X, padx=4, pady=4)

        self._entry = tk.Entry(input_frame)
        self._entry.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4)
        )
        self._entry.bind("<Return>", self._on_enter)

        self._send_btn = tk.Button(
            input_frame,
            text="Отправить",
            command=self._on_send_click,
        )
        self._send_btn.pack(side=tk.LEFT)

        self._mic_callback = None
        self._mic_btn = tk.Button(
            input_frame,
            text="\U0001f3a4",
            command=self._on_mic_click,
        )
        self._mic_btn.pack(side=tk.LEFT, padx=(4, 0))

        self._voice_mode = False
        self._voice_var = tk.BooleanVar(value=False)
        self._voice_toggle = tk.Checkbutton(
            input_frame,
            text="\U0001f50a",
            variable=self._voice_var,
            command=self._on_voice_toggle,
        )
        self._voice_toggle.pack(side=tk.LEFT, padx=(4, 0))

        self._status_var = tk.StringVar(value="Оффлайн")
        self._status_label = tk.Label(
            self._root,
            textvariable=self._status_var,
            anchor=tk.W,
            relief=tk.SUNKEN,
            padx=4,
        )
        self._status_label.pack(
            fill=tk.X, side=tk.BOTTOM
        )

    def show(self):
        self._root.deiconify()
        self._root.lift()
        self._entry.focus_set()

    def hide(self):
        self._root.withdraw()

    def is_visible(self):
        return bool(
            self._root.winfo_viewable()
        )

    def show_history(self, messages):
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)

        for item in messages:
            sender = item.get("sender", "EddieAI")
            text = item.get("text", "")
            ts = (item.get("ts") or "")[11:16]
            read = item.get("read", False)

            if sender == "EddieAI":
                tag = "ai"
                ts_tag = "ai_ts"
            else:
                tag = "user"
                ts_tag = "user_ts"

            ts_line = f"[{ts}]\n"
            self._text.insert(
                tk.END, ts_line, ts_tag
            )

            body = text + "\n"

            if (
                sender == "Eddie"
                and read
            ):
                body += "  ✓✓ прочитано\n"
            elif sender == "Eddie":
                body += "  ✓\n"

            self._text.insert(
                tk.END, body + "\n", tag
            )

        self._text.configure(state=tk.DISABLED)
        self._text.see(tk.END)

    def append_message(self, sender, text, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M")

        self._text.configure(state=tk.NORMAL)

        if sender == "EddieAI":
            tag = "ai"
            ts_tag = "ai_ts"
        else:
            tag = "user"
            ts_tag = "user_ts"

        ts_line = f"[{timestamp}]\n"
        self._text.insert(tk.END, ts_line, ts_tag)

        body = text + "\n"

        if sender == "Eddie":
            body += "  ✓\n"

        self._text.insert(
            tk.END, body + "\n", tag
        )

        self._text.configure(state=tk.DISABLED)
        self._text.see(tk.END)

    def mark_eddie_read(self):
        self._text.configure(state=tk.NORMAL)

        content = self._text.get(
            "1.0", tk.END
        )

        idx = content.rfind(
            "✓\n", 0, len(content)
        )

        if idx != -1:
            start = f"1.0 + {idx}c"
            end = f"1.0 + {idx + 2}c"

            if (
                self._text.get(start, end)
                == "✓\n"
            ):
                self._text.delete(
                    start, end
                )
                self._text.insert(
                    start, "✓✓ прочитано\n"
                )

        self._text.configure(state=tk.DISABLED)

    def set_status(self, text):
        self._status_var.set(text)

    def on_send(self, callback):
        self._send_callback = callback

    def _on_enter(self, event=None):
        self._on_send_click()

    def _on_send_click(self):
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, tk.END)
        if self._send_callback:
            self._send_callback(text)

    def on_mic(self, callback):
        self._mic_callback = callback

    def _on_mic_click(self):
        if self._mic_callback:
            self._mic_callback()

    def _on_voice_toggle(self):
        self._voice_mode = self._voice_var.get()

    def is_voice_mode(self):
        return self._voice_mode

    def _on_close(self):
        self.hide()
