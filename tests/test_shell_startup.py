import re
from pathlib import Path

from wcgw.client.bash_state.bash_state import (
    PROMPT_CONST,
    _shell_launch_argv,
    ensure_wcgw_block_in_rc_file,
    generate_thread_id,
    start_shell,
)
from wcgw.types_ import Console


class RecordingConsole(Console):
    def __init__(self) -> None:
        self.logs: list[str] = []
        self.prints: list[str] = []

    def log(self, msg: str) -> None:
        self.logs.append(msg)

    def print(self, msg: str) -> None:
        self.prints.append(msg)


def test_systemd_scope_only_changes_resource_accounting(monkeypatch) -> None:
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.platform.system", lambda: "Linux"
    )
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.shutil.which",
        lambda command: "/usr/bin/systemd-run" if command == "systemd-run" else None,
    )
    monkeypatch.delenv("WCGW_SHELL_SYSTEMD_SCOPE", raising=False)
    monkeypatch.delenv("WCGW_SHELL_MEMORY_HIGH", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.os.path.exists",
        lambda path: path == "/run/user/1000/systemd/private",
    )

    argv = _shell_launch_argv(["/usr/bin/zsh"], RecordingConsole())

    assert argv[:5] == [
        "/usr/bin/systemd-run",
        "--user",
        "--scope",
        "--quiet",
        "--collect",
    ]
    assert argv[-1] == "/usr/bin/zsh"
    joined = " ".join(argv)
    for sandbox_property in (
        "ProtectSystem",
        "ProtectHome",
        "PrivateNetwork",
        "PrivateDevices",
        "NoNewPrivileges",
        "CapabilityBoundingSet",
        "RestrictNamespaces",
        "MemoryMax",
    ):
        assert sandbox_property not in joined


def test_systemd_scope_can_apply_soft_memory_pressure(monkeypatch) -> None:
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.platform.system", lambda: "Linux"
    )
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.shutil.which",
        lambda command: "/usr/bin/systemd-run" if command == "systemd-run" else None,
    )
    monkeypatch.delenv("WCGW_SHELL_SYSTEMD_SCOPE", raising=False)
    monkeypatch.setenv("WCGW_SHELL_MEMORY_HIGH", "3G")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.os.path.exists",
        lambda path: path == "/run/user/1000/systemd/private",
    )

    argv = _shell_launch_argv(["/usr/bin/zsh"], RecordingConsole())

    assert "MemoryHigh=3G" in argv
    assert all(not value.startswith("MemoryMax=") for value in argv)


def test_systemd_scope_auto_falls_back_without_user_manager(monkeypatch) -> None:
    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state.platform.system", lambda: "Linux"
    )
    monkeypatch.delenv("WCGW_SHELL_SYSTEMD_SCOPE", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert _shell_launch_argv(["/usr/bin/zsh"], RecordingConsole()) == [
        "/usr/bin/zsh"
    ]


def test_systemd_scope_can_be_disabled_without_restricting_shell(monkeypatch) -> None:
    monkeypatch.setenv("WCGW_SHELL_SYSTEMD_SCOPE", "off")
    assert _shell_launch_argv(["/usr/bin/zsh"], RecordingConsole()) == [
        "/usr/bin/zsh"
    ]


def test_fallback_shell_preserves_initial_directory(tmp_path: Path) -> None:
    shell, _ = start_shell(
        False,
        str(tmp_path),
        RecordingConsole(),
        False,
        "/definitely/not-a-shell",
    )
    try:
        shell.sendline("pwd")
        shell.expect(re.escape(str(tmp_path)), timeout=3)
        shell.expect(PROMPT_CONST, timeout=3)
    finally:
        shell.close(force=True)


def test_fallback_shell_uses_scoped_launcher_and_closes_failed_shell(
    monkeypatch, tmp_path: Path
) -> None:
    class FakeShell:
        def __init__(self, fail: bool) -> None:
            self.fail = fail
            self.closed = False

        def setecho(self, enabled: bool) -> None:
            return None

        def sendline(self, statement: str) -> None:
            return None

        def expect(self, pattern, timeout: float) -> int:
            if self.fail:
                raise RuntimeError("prompt setup failed")
            return 0

        def close(self, force: bool) -> None:
            self.closed = force

    failed_shell = FakeShell(True)
    fallback_shell = FakeShell(False)
    launches: list[list[str]] = []

    def fake_spawn_shell(shell_argv, overrideenv, initial_dir, console):
        launches.append(shell_argv)
        return failed_shell if len(launches) == 1 else fallback_shell

    monkeypatch.setattr(
        "wcgw.client.bash_state.bash_state._spawn_shell", fake_spawn_shell
    )

    shell, _ = start_shell(
        False,
        str(tmp_path),
        RecordingConsole(),
        False,
        "/usr/bin/zsh",
    )

    assert shell is fallback_shell
    assert failed_shell.closed
    assert launches == [
        ["/usr/bin/zsh"],
        ["/bin/bash", "--noprofile", "--norc"],
    ]


def test_zsh_block_upgrades_existing_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    zshrc = tmp_path / ".zshrc"
    zshrc.write_text(
        "before\n"
        "# --WCGW_ENVIRONMENT_START--\n"
        "if [ -n \"$IN_WCGW_ENVIRONMENT\" ]; then\n"
        " old-wcgw-hook\n"
        "fi\n"
        "# --WCGW_ENVIRONMENT_END--\n"
        "after\n"
    )

    ensure_wcgw_block_in_rc_file("/usr/bin/zsh", RecordingConsole())

    content = zshrc.read_text()
    assert "before\n" in content
    assert "after\n" in content
    assert "old-wcgw-hook" not in content
    assert "autoload -Uz add-zsh-hook" in content
    assert "add-zsh-hook -d precmd prmptcmdwcgw" in content
    assert "add-zsh-hook precmd prmptcmdwcgw" in content


def test_generated_thread_id_has_collision_resistant_shape() -> None:
    assert re.fullmatch(r"i[0-9a-f]{32}", generate_thread_id()) is not None
