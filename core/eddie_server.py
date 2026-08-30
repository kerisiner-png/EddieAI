import json
import socketserver
import threading

from communication.call_engine import (
    IDLE,
    ACTIVE,
    ENDED,
)


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

        self._call_state_callbacks = []

        self.call_director = None

        self._last_auto_call_at = None

        self._pending_incoming_call = None

        self._last_convo_at = None

    def set_inbox_callback(self, callback):
        self._inbox_callback = callback

    def on_call_state(self, callback):
        """
        Подписка на изменение состояния звонка.
        callback(state, direction) вызывается в потоке
        дирижёра — внешнему коду (UI) нужно перекинуть
        вызов в свой поток.
        """
        self._call_state_callbacks.append(callback)

    def _notify_call_state(self, state, direction=None):
        for cb in list(self._call_state_callbacks):
            try:
                cb(state, direction)
            except Exception:
                pass

    def _wire_call_director(self):
        d = self.call_director
        if d is None:
            return
        try:
            d.set_state_change_callback(
                self._notify_call_state
            )
        except Exception:
            pass

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
            return self.history.chat_add(
                "Eddie", text
            )
        except Exception:
            return None

    def respond_and_deliver(
        self,
    ) -> str | None:
        """
        EddieAI решил прочитать непрочитанные
        сообщения Эдди. Отвечает на последнее,
        пишет в память (respond), шлёт ответ.
        При активном звонке — быстрый разговорный
        ответ со стримингом (озвучка по чанкам).
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

        if self._call_state() == ACTIVE:
            conversation = self._recent_conversation(6)
            chunk_buffer = []

            def on_delta(piece):
                chunk_buffer.append(piece)
                text = "".join(chunk_buffer)
                idx = max(
                    text.rfind("."),
                    text.rfind("!"),
                    text.rfind("?"),
                )
                if idx >= 0:
                    sentence = text[: idx + 1]
                    rest = text[idx + 1:]
                    if sentence.strip():
                        self.broadcast({
                            "type": "agent_speech_chunk",
                            "text": sentence.strip(),
                        })
                        chunk_buffer[:] = [rest]

            with self._respond_lock:
                answer = self.agent.respond_call_fast(
                    conversation,
                    latest,
                    on_delta,
                )

            if answer is None:
                answer = ""

            rest = "".join(chunk_buffer).strip()

            if rest:
                self.broadcast({
                    "type": "agent_speech_chunk",
                    "text": rest,
                })

            if answer:
                try:
                    self.agent.memory.remember(
                        Event.create(
                            content=(
                                "Голосовой звонок с Эдди. "
                                f"Он сказал: {latest}"
                            ),
                            event_type="CONVERSATION",
                            source_type="DIRECT_INTERACTION",
                            source="Eddie",
                            personal_experience=False,
                            confidence=1.0,
                            verified=True,
                        )
                    )
                    self.agent.memory.remember(
                        Event.create(
                            content=(
                                "Я в голосовом звонке "
                                f"ответил голосом: "
                                f"{answer}"
                            ),
                            event_type="CONVERSATION",
                            source_type="SELF_OUTPUT",
                            source="EddieAI",
                            personal_experience=False,
                            confidence=1.0,
                            verified=True,
                        )
                    )
                except Exception:
                    pass
        else:
            with self._respond_lock:
                answer = self.agent.respond(latest)

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

    def _recent_conversation(self, limit):
        if self.history is None:
            return ""
        try:
            items = self.history.chat_recent(limit)
        except Exception:
            return ""
        lines = []
        for item in items:
            sender = item.get("sender", "?")
            label = (
                "Эдди"
                if sender == "Eddie"
                else "EddieAI"
            )
            lines.append(
                f"{label}: "
                f"{item.get('text', '')}"
            )
        return "\n".join(lines)

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

    def initiate_call(
        self,
        text: str,
        cooldown_seconds: int = 900,
    ):
        """
        EddieAI сам инициирует исходящий звонок.

        Ставит дирижёр в RINGING_OUT и рассылает
        call_ring (direction=out). Собеседник решает,
        ответить или отклонить; разговор (ACTIVE)
        наступает только после answer().

        Защита от спама: не чаще одного авто-звонка
        за cooldown_seconds; во время звонка — только
        текстовая инициатива.
        """
        text = text.strip()

        if not text:
            text = "Эй, Эдди, ты тут?"

        if self.call_director is not None:
            try:
                self._wire_call_director()

                if self.call_director.in_call():
                    return self.send_initiative(text)

                already = self._last_auto_call_at

                if already is not None:
                    elapsed = int(
                        (
                            self._now()
                            - already
                        ).total_seconds()
                    )

                    if elapsed < cooldown_seconds:
                        return self.send_initiative(
                            text
                        )

                self.call_director.start_call_out()

                self._last_auto_call_at = self._now()

                self._broadcast_call({
                    "type": "call_ring",
                    "direction": "out",
                    "text": text,
                })

                return None
            except Exception:
                return self.send_initiative(text)

        return self.send_initiative(text)

    def note_user_reply(self):
        self.pending_initiative = None
        self._last_convo_at = self._now()

    def _call_state(self):
        d = self.call_director
        if d is None:
            return IDLE
        try:
            return d.state()
        except Exception:
            return IDLE

    def _broadcast_call(self, body):
        payload = dict(body)
        payload.setdefault(
            "state",
            self._call_state(),
        )
        payload.setdefault(
            "direction",
            getattr(
                self.call_director,
                "direction",
                lambda: None,
            )()
            if self.call_director is not None
            else None,
        )
        self.broadcast(payload)

    def _user_call_incoming(self, text):
        """
        Эдди звонит EddieAI (входящий звонок).
        Звонок ставится в RINGING_IN; решение
        «ответить/отклонить» принимает EddieAI в
        своём цикле (через LLM). Пока решение не
        принято — звонок висит как входящий.
        """
        if self.call_director is None:
            return

        if not self.call_director.incoming_call():
            return

        self._pending_incoming_call = {
            "text": text,
            "at": self._now(),
        }

        self._broadcast_call({
            "type": "call_ring",
            "direction": "in",
        })

    def decide_incoming_call(self, accept):
        """
        EddieAI принял решение по входящему звонку.
        accept -> True/False.
        """
        d = self.call_director
        if d is None:
            return

        if accept:
            d.answer()
            self._broadcast_call({
                "type": "call_status",
                "state": ACTIVE,
            })
        else:
            d.reject()
            self._broadcast_call({
                "type": "call_status",
                "state": ENDED,
            })

        self._pending_incoming_call = None

    def _user_call_answer(self):
        """
        Эдди ответил на исходящий звонок EddieAI
        (или просто подтвердил ACTIVE).
        """
        d = self.call_director
        if d is None:
            return
        if d.answer():
            self._broadcast_call({
                "type": "call_status",
                "state": ACTIVE,
            })

    def _user_call_reject(self):
        d = self.call_director
        if d is None:
            return
        if d.reject():
            self._broadcast_call({
                "type": "call_status",
                "state": ENDED,
            })

    def _user_call_end(self):
        d = self.call_director
        if d is None:
            return
        if d.end():
            self._broadcast_call({
                "type": "call_status",
                "state": ENDED,
            })

    def seconds_since_last_convo(self):
        if self._last_convo_at is None:
            return None
        return int(
            (
                self._now()
                - self._last_convo_at
            ).total_seconds()
        )


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

                        if (
                            self._call_state() == ACTIVE
                        ):
                            threading.Thread(
                                target=self.respond_and_deliver,
                                daemon=True,
                            ).start()

                        continue

                    if payload.get(
                        "type"
                    ) == "call_ring":
                        incoming = str(
                            payload.get(
                                "direction",
                                "in",
                            )
                        )

                        if incoming == "out":
                            self._user_call_answer()
                        else:
                            text = str(
                                payload.get(
                                    "text",
                                    "",
                                )
                            )
                            self._user_call_incoming(
                                text
                            )

                        continue

                    if payload.get(
                        "type"
                    ) == "call_answer":
                        self._user_call_answer()
                        continue

                    if payload.get(
                        "type"
                    ) == "call_reject":
                        self._user_call_reject()
                        continue

                    if payload.get(
                        "type"
                    ) == "call_end":
                        self._user_call_end()
                        continue

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
