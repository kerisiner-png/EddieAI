import os
import sys
import threading
import traceback

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil

    PYWIN32 = True
except Exception:
    PYWIN32 = False

_SERVICE_BASE = (
    win32serviceutil.ServiceFramework
    if PYWIN32
    else object
)


def _log(msg):
    if PYWIN32:
        try:
            servicemanager.LogInfoMsg(msg)
        except Exception:
            pass
    try:
        from datetime import datetime
        with open(
            os.path.join(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(__file__)
                    )
                ),
                "logs",
                "eddie_service.log",
            ),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"{msg}\n"
            )
    except Exception:
        pass


class EddieService(_SERVICE_BASE):
    _svc_name_ = "EddieAI"
    _svc_display_name_ = "EddieAI Persistent Runtime"
    _svc_description_ = (
        "Постоянный фоновый рантайм цифровой "
        "личности EddieAI: автономный цикл, "
        "восприятие экрана, совместная жизнь "
        "и TCP-порт 7778 для чата и голоса."
    )

    def __init__(self, args):
        super().__init__(args)
        self.agent = None
        self.runtime = None
        self.fault_tolerance = None
        self._server = None
        self._fault_stop = threading.Event()
        self._fault_thread = None

    @classmethod
    def _build_runtime(cls):
        from core.agent import Agent
        from core.autonomy_runtime_factory import (
            AutonomyRuntimeFactory,
        )
        from core.fault_tolerance import (
            FaultTolerance,
        )

        agent = Agent()

        runtime = AutonomyRuntimeFactory(
            agent,
            enable_decision_core=True,
        ).build()

        fault_tolerance = FaultTolerance(
            runtime
        )

        return (
            agent,
            runtime,
            fault_tolerance,
        )

    def _start_server(self):
        server = getattr(
            self.runtime,
            "eddie_server",
            None,
        )

        if server is None:
            _log("eddie_server отсутствует")
            return None

        return server.serve_forever()

    def _watchdog(self):
        while not self._fault_stop.is_set():
            try:
                if self.fault_tolerance is not None:
                    self.fault_tolerance.update_heartbeat()
                    self.fault_tolerance.auto_reset_error()
            except Exception as exc:
                _log(
                    "watchdog error: "
                    f"{type(exc).__name__}: {exc}"
                )

            self._fault_stop.wait(timeout=30.0)

    def SvcInit(self, event):
        self._stop_event = event

        if PYWIN32:
            self.ReportServiceStatus(
                win32service.SERVICE_START_PENDING
            )

        _log("EddieAI service starting")

    def SvcDoRun(self):
        if PYWIN32:
            self.ReportServiceStatus(
                win32service.SERVICE_RUNNING
            )

        self._stop_event.clear()

        try:
            (
                self.agent,
                self.runtime,
                self.fault_tolerance,
            ) = self._build_runtime()
        except Exception as exc:
            _log(
                "runtime init failed: "
                f"{type(exc).__name__}: {exc}"
            )
            traceback.print_exc(file=sys.stderr)
            return

        try:
            self.runtime.start_background_loop()
            _log("autonomy loop started")
        except Exception as exc:
            _log(
                "autonomy loop start failed: "
                f"{type(exc).__name__}: {exc}"
            )

        try:
            self._server = self._start_server()
            _log("eddie server started")
        except Exception as exc:
            _log(
                "eddie server start failed: "
                f"{type(exc).__name__}: {exc}"
            )

        self._fault_thread = threading.Thread(
            target=self._watchdog,
            name="EddieAI-Watchdog",
            daemon=True,
        )
        self._fault_thread.start()
        _log("watchdog started")

        _log("EddieAI service running")

        while (
            not self._stop_event.is_set()
        ):
            if PYWIN32:
                self._stop_event.wait(
                    timeout=1000
                )
            else:
                self._stop_event.wait(
                    timeout=1.0
                )

        _log("EddieAI service stopping")
        self._shutdown()

    def _shutdown(self):
        self._fault_stop.set()

        if self._fault_thread is not None:
            self._fault_thread.join(
                timeout=2.0
            )

        try:
            if self.runtime is not None:
                self.runtime.stop_background_loop()
        except Exception as exc:
            _log(
                "stop loop error: "
                f"{type(exc).__name__}: {exc}"
            )

        try:
            if self._server is not None:
                self._server.shutdown()
                self._server.server_close()
        except Exception as exc:
            _log(
                "server shutdown error: "
                f"{type(exc).__name__}: {exc}"
            )

        try:
            if self.agent is not None:
                self.agent.close()
        except Exception as exc:
            _log(
                "agent close error: "
                f"{type(exc).__name__}: {exc}"
            )

        _log("EddieAI service stopped")

        if PYWIN32:
            self.ReportServiceStatus(
                win32service.SERVICE_STOPPED
            )

    def SvcStop(self):
        _log("SvcStop requested")
        self._stop_event.set()

        if PYWIN32:
            self.ReportServiceStatus(
                win32service.SERVICE_STOP_PENDING
            )
