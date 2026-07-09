from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence


class ProviderError(RuntimeError):
    pass


class BaseProvider:
    name = "base"

    def complete(self, prompt: str, role: str = "worker", timeout_s: int = 120) -> str:
        raise NotImplementedError


class DeterministicProvider(BaseProvider):
    """No-key fallback provider.

    It does not pretend to be an LLM. It lets the DQE kernel run end-to-end
    without external dependencies and is useful for tests, demos, and offline
    orchestration checks.
    """

    name = "deterministic"

    def complete(self, prompt: str, role: str = "worker", timeout_s: int = 120) -> str:
        first_line = prompt.strip().splitlines()[0] if prompt.strip() else "задача"
        return (
            f"Роль: {role}.\n"
            f"Черновой вывод по запросу: {first_line[:180]}.\n"
            "Этот ответ создан детерминированным provider'ом; для реального усиления качества "
            "подключите внешний CLI/provider, но ядро проверки и сборки уже выполняется."
        )


@dataclass
class CLIProvider(BaseProvider):
    command: Sequence[str]
    name: str = "cli"

    def complete(self, prompt: str, role: str = "worker", timeout_s: int = 120) -> str:
        if not self.command:
            raise ProviderError("CLI command is empty")
        try:
            proc = subprocess.run(
                list(self.command),
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"CLI provider timeout after {timeout_s}s") from exc
        except OSError as exc:
            raise ProviderError(f"Cannot start CLI provider: {exc}") from exc

        if proc.returncode != 0:
            stderr = proc.stderr.strip()[:2000]
            raise ProviderError(f"CLI provider exited with {proc.returncode}: {stderr}")
        output = proc.stdout.strip()
        if not output:
            raise ProviderError("CLI provider returned empty output")
        return output


def make_provider(provider_cmd: Optional[str]) -> BaseProvider:
    if not provider_cmd:
        return DeterministicProvider()
    # Simple shell-like split without invoking a shell.
    import shlex

    return CLIProvider(command=shlex.split(provider_cmd))
