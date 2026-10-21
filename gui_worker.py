"""One run per process, with JSON events for the desktop GUI. Copyright Ayulog."""
import contextlib
import json
import sys
import threading

_output = sys.stdout
_output_lock = threading.Lock()


def emit(event):
    with _output_lock:
        _output.write(json.dumps(event, ensure_ascii=True) + '\n')
        _output.flush()


def main(mode='download'):
    try:
        import auth
        import downloader
        import ui
        from rich.text import Text
        ui.console.file = sys.stderr
        ui.console._force_terminal = False
        finished = threading.Event()

        def listen():
            for line in sys.stdin:
                if line.strip() == 'stop':
                    auth.stop_event.set()
            # Parent closed the pipe: do not leave an orphan download running.
            auth.stop_event.set()

        def snapshot():
            with ui.stats_lock:
                stats = dict(ui.stats)
            tasks = []
            for task in ui.progress.tasks:
                tasks.append({'id': task.id, 'name': Text.from_markup(task.description).plain.strip(),
                              'total': task.total or 0, 'completed': task.completed,
                              'speed': task.speed or 0, 'status': Text.from_markup(task.fields.get('status', '')).plain})
            emit({'type': 'snapshot', 'stats': stats, 'tasks': tasks})

        original_log = ui.log

        def log(level, message):
            original_log(level, message)
            cookie = downloader.NEXUS_SESSION_COOKIE
            message = message.replace(cookie, '[hidden]') if cookie else message
            emit({'type': 'log', 'level': level, 'message': message})

        ui.log = downloader.log = log
        import nexus
        nexus.log = log

        def report():
            while not finished.wait(0.3):
                snapshot()

        # In normal GUI use stdin is held open until process exit.
        listener = threading.Thread(target=listen, daemon=True)
        listener.start()
        reporter = threading.Thread(target=report, daemon=True)
        reporter.start()
        try:
            with contextlib.redirect_stdout(sys.stderr):
                emit({'type': 'state', 'state': 'authenticating'})
                if mode == 'login':
                    auth.get_token()
                    emit({'type': 'state', 'state': 'authenticated'})
                else:
                    if not downloader.NEXUS_SESSION_COOKIE:
                        raise ValueError('请先填写 nexusmods_session Cookie。')
                    if not downloader.read_mod_list():
                        raise ValueError('没有可下载的 MOD 链接。')
                    original_get_token = downloader.get_token

                    def token():
                        result = original_get_token()
                        emit({'type': 'state', 'state': 'authenticated'})
                        emit({'type': 'state', 'state': 'running'})
                        return result

                    downloader.get_token = token
                    downloader.run(headless=True)
            state = 'stopped' if auth.stop_event.is_set() else ('failed' if ui.stats['failed'] else 'done')
        except InterruptedError:
            state = 'stopped'
        except Exception as exc:
            # Authentication server responses may contain credentials: expose the
            # exception class only; download details arrive through ordinary logs.
            emit({'type': 'error', 'message': f'操作失败（{type(exc).__name__}）。请检查配置、网络或重新授权；下载错误见日志。'})
            state = 'stopped' if auth.stop_event.is_set() else 'failed'
        finally:
            finished.set()
            reporter.join()
        snapshot()
        emit({'type': 'result', 'state': state})
        return 1 if state == 'failed' else 0
    except Exception as exc:
        emit({'type': 'error', 'message': f'后台启动失败（{type(exc).__name__}），请运行 Setup-GUI.cmd 检查依赖和 config.toml。'})
        emit({'type': 'result', 'state': 'failed'})
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'download'))
