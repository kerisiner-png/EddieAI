import json
import socketserver
import threading


class EddieServer:
    """
    Единая точка жизни EddieAI:

    - один Agent (личность, память, автономия);
    - TCP-сервер на localhost для органов
      ввода-вывода (чат, голос);

    Протокол: построчный JSON.
    Клиент -> сервер:
        {"type": "user_message", "text": "..."}
    Сервер -> клиенту:
        {"type": "agent_message", "text": "..."}
    Сервер -> всем подключённым (инициатива):
        {"type": "agent_initiative", "text": "..."}
    """

    def __init__(
        self,
        agent,
        host="127.0.0.1",
        port=7778,
        history_store=None,
    ):
        import datetime

        self.datetime = datetime

        self.agent = agent
        self.host = host
        self.port = port
        self.history = history_store

        self._clients = []
        self._clients_lock = (
            threading.Lock()
        )

        self._respond_lock = (
            threading.Lock()
        )

        self.outbox = []

        self.pending_initiative = None

        self.eddie_absent_since = None

        self._inbox_callback = None

    def set_inbox_callback(self, callback):
        self._inbox_callback = callback

    # ---------------------------------------------
    # ПРИСУТСТВИЕ ЭДДИ
    # ---------------------------------------------

    def _now(self):
        return (
            self.datetime.datetime.now(
                self.datetime.timezone.utc
            )
        )

    def note_eddie_arrived(self):
        absent = None

        if (
            self.eddie_absent_since
            is not None
        ):
            absent = int(
                (
                    self._now()
                    - self.eddie_absent_since
                ).total_seconds()
            )

        self.eddie_absent_since = None

        text = "Эдди сел за компьютер."

        if absent is not None:
            if absent >= 60:
                minutes = absent // 60

                text = (
                    f"Эдди вернулся после "
                    f"{minutes} мин отсутствия "
                    f"и сел за компьютер."
                )
            else:
                text = (
                    "Эдди вернулся и сел "
                    "за компьютер."
                )

        try:
            from memory.events import Event

            self.agent.memory.remember(
                Event.create(
                    content=text,
                    event_type="PRESENCE",
                    source_type="SYSTEM",
                    source="SYSTEM",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                )
            )
        except Exception:
            pass

        return text

    def note_eddie_left(self):
        if (
            self.eddie_absent_since
            is None
        ):
            self.eddie_absent_since = (
                self._now()
            )

        try:
            from memory.events import Event

            self.agent.memory.remember(
                Event.create(
                    content=(
                        "Эдди отошёл от компьютера."
                    ),
                    event_type="PRESENCE",
                    source_type="SYSTEM",
                    source="SYSTEM",
                    personal_experience=False,
                    confidence=1.0,
                    verified=True,
                )
            )
        except Exception:
            pass

    # ---------------------------------------------
    # КЛИЕНТЫ
    # ---------------------------------------------

    def _register(
        self,
        writer,
    ) -> bool:
        with self._clients_lock:
            self._clients.append(writer)

            return (
                len(self._clients) == 1
            )

    def _unregister(
        self,
        writer,
    ) -> bool:
        with self._clients_lock:
            if writer in self._clients:
                self._clients.remove(
                    writer
                )

            return (
                len(self._clients) == 0
            )

    def broadcast(
        self,
        payload: dict,
        only_connected=True,
    ):
        line = (
            json.dumps(
                payload,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")

        dead = []

        with self._clients_lock:
            targets = list(self._clients)

        seen = set()

        for writer in targets:
            if id(writer) in seen:
                continue

            seen.add(id(writer))

            try:
                writer.write(line)
                writer.flush()
            except Exception:
                dead.append(writer)

        for writer in dead:
            self._unregister(writer)

        if not only_connected:
            return

    # ---------------------------------------------
    # ОБРАБОТКА ВХОДЯЩЕГО
    # ---------------------------------------------

    def handle_user_message(
        self,
        text: str,
    ) -> int:
        """
        Eddie пишет. Сообщение кладётся в чат-историю
        как непрочитанное для EddieAI. respond() НЕ
        вызывается — EddieAI решает прочитать сам
        в своём цикле (respond_and_deliver).
        Возвращает msg_id.
        """
        if self.history is None:
            return None

        try:
            msg_id = self.history.chat_add(
                "Eddie", text
            )
        except Exception:
            return None

        try:
            runtime = getattr(
                self.agent,
                "autonomous_runtime",
                None,
            )

            if runtime is not None:
                runtime.notify_inbox()
        except Exception:
            pass

        return msg_id

    def respond_and_deliver(
        self,
    ) -> str | None:
        """
        EddieAI решил прочитать непрочитанные
        сообщения Эдди. Отвечает на последнее,
        пишет в память (respond), шлёт ответ.
        Возвращает ответ или None.
        """
        if self.history is None:
            return None

        unread = self.history.chat_unread_eddie()

        if not unread:
            return None

        for item in unread:
            try:
                self.history.chat_mark_eddie_read(
                    item["id"]
                )
            except Exception:
                pass

        latest = unread[-1]["text"]

        with self._respond_lock:
            answer = self.agent.respond(
                latest
            )

        ai_id = None

        try:
            ai_id = self.history.chat_add(
                "EddieAI", answer
            )
        except Exception:
            ai_id = None

        self.broadcast({
            "type": "agent_message",
            "msg_id": ai_id,
            "text": answer,
        })

        return answer

    # ---------------------------------------------
    # ИНИЦИАТИВА
    # ---------------------------------------------

    def send_initiative(
        self,
        text: str,
    ):
        """
        EddieAI сам обращается к Эдди.

        Доставляется всем подключённым органам
        (чат/голос-клиенты). Ответ ожидается;
        если его долго нет — вызывающая сторона
        (check_pending) фиксирует отсутствие Эдди.
        """

        text = text.strip()

        if not text:
            return None

        self.pending_initiative = {
            "text": text,
            "at": (
                self.datetime.datetime.now(
                    self.datetime.timezone.utc
                )
            ),
            "answered": False,
        }

        try:
            import winsound

            winsound.MessageBeep(
                winsound.MB_ICONASTERISK
            )
        except Exception:
            pass

        ai_id = None

        if self.history is not None:
            try:
                ai_id = self.history.chat_add(
                    "EddieAI", text
                )
            except Exception:
                ai_id = None

        self.broadcast({
            "type": "agent_initiative",
            "msg_id": ai_id,
            "text": text,
        })

        if not self._clients:
            self.outbox.append(text)

        return self.pending_initiative

    def note_user_reply(self):
        self.pending_initiative = None

    def check_pending_initiative(
        self,
        timeout_seconds: int = 600,
    ):
        """
        Вызывается периодически внешним циклом.

        Если инициатива висит без ответа дольше
        таймаута — фиксируется в памяти личности:
        «обратился — ответа нет».
        """

        pending = self.pending_initiative

        if (
            pending is None
            or pending.get("answered")
        ):
            return None

        elapsed = int(
            (
                self._now()
                - pending["at"]
            ).total_seconds()
        )

        if elapsed < timeout_seconds:
            return None

        text = (
            f"Я обратился к Эдди "
            f"({pending['text'][:120]}), но ответа "
            f"не последовало уже {elapsed // 60} мин. "
            f"Вероятно, его сейчас нет за "
            f"компьютером, или он меня не услышал."
        )

        try:
            from memory.events import Event

            self.agent.memory.remember(
                Event.create(
                    content=text,
                    event_type="CONVERSATION",
                    source_type="SELF_OUTPUT",
                    source="self",
                    personal_experience=False,
                    confidence=0.8,
                    verified=True,
                )
            )
        except Exception:
            pass

        self.pending_initiative["answered"] = True

        self.pending_initiative = None

        return text

    def flush_outbox(self):
        if not self.outbox:
            return

        pending = list(self.outbox)

        self.outbox.clear()

        for text in pending:
            self.send_initiative(text)

    # ---------------------------------------------
    # СЕРВЕР
    # ---------------------------------------------

    def serve_forever(self):
        class Handler(
            socketserver.StreamRequestHandler,
        ):
            server_ref = self

            def handle(handler_self):
                writer = handler_self.wfile

                self._register(writer)

                try:
                    self.flush_outbox()
                except Exception:
                    pass

                if self.history is not None:
                    try:
                        writer.write(
                            (
                                json.dumps({
                                    "type": "history",
                                    "messages": (
                                        self.history
                                        .chat_recent(
                                            50
                                        )
                                    ),
                                }, ensure_ascii=False)
                                + "\n"
                            ).encode("utf-8")
                        )

                        writer.flush()
                    except Exception:
                        pass

                while True:
                    try:
                        line = (
                            handler_self.rfile.readline()
                        )
                    except Exception:
                        break

                    if not line:
                        break

                    line = line.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()

                    if not line:
                        continue

                    try:
                        payload = json.loads(
                            line
                        )
                    except json.JSONDecodeError:
                        continue

                    if payload.get(
                        "type"
                    ) == "mark_read":
                        msg_id = (
                            payload.get(
                                "msg_id"
                            )
                        )

                        if (
                            msg_id is not None
                            and self.history
                            is not None
                        ):
                            try:
                                self.history.chat_mark_read(
                                    msg_id
                                )
                            except Exception:
                                pass

                        continue

                    if payload.get(
                        "type"
                    ) == "user_message":
                        text = str(
                            payload.get(
                                "text",
                                "",
                            )
                        )

                        if not text:
                            continue

                        try:
                            self.handle_user_message(
                                text
                            )
                        except Exception as exc:
                            try:
                                writer.write(
                                    (
                                        json.dumps({
                                            "type": "error",
                                            "text": str(exc),
                                        }, ensure_ascii=False)
                                        + "\n"
                                    ).encode("utf-8")
                                )
                                writer.flush()
                            except Exception:
                                break

            def finish(handler_self):
                self._unregister(
                    handler_self.wfile
                )

                super().finish()

        class Server(
            socketserver.ThreadingTCPServer,
        ):
            allow_reuse_address = True
            daemon_threads = True

        server = Server(
            (self.host, self.port),
            Handler,
        )

        thread = threading.Thread(
            target=server.serve_forever,
            name="EddieAI-Server",
            daemon=True,
        )

        thread.start()

        return server


if __name__ == "__main__":
    import sys
    sys.path.insert(0, r"C:\EddieAI")
    from core.agent import Agent
    agent = Agent()
    server = EddieServer(agent)
    print(f"EddieServer running on port {server.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
