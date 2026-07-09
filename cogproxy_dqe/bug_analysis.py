from __future__ import annotations

"""Bug analysis pack support.

This module is intentionally user-facing: a client may have only a log and a
stacktrace. CogProxy DQE should turn that into a compact evidence bundle for a
model and a useful offline report when no model is connected.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .models import TaskContract, WorkerResult
from .providers import BaseProvider, DeterministicProvider, ProviderError

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs", ".cs", ".php", ".rb",
    ".sql", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".properties", ".xml",
}
DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build",
    "target", ".mypy_cache", ".pytest_cache", ".idea", ".vscode", "coverage", ".next", ".tox", "out", "reports",
}
MAX_FILE_BYTES = 320_000
MAX_INDEX_FILES = 1200


@dataclass
class StackFrame:
    file: str
    line: int
    function: str = ""
    code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectFile:
    path: str
    rel_path: str
    kind: str
    size: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceSnippet:
    ref: str
    file: str
    start_line: int
    end_line: int
    text: str
    reason: str
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BugHypothesis:
    title: str
    confidence: float
    evidence_refs: List[str]
    explanation: str
    verification_steps: List[str]
    fix_plan: List[str]
    risk: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BugAnalysisResult:
    exception_type: str
    exception_message: str
    frames: List[StackFrame]
    indexed_files: List[ProjectFile]
    evidence: List[EvidenceSnippet]
    hypotheses: List[BugHypothesis]
    model_prompt: str
    model_answer: Optional[str]
    provider_called: bool
    report: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "frames": [f.to_dict() for f in self.frames],
            "indexed_files": [f.to_dict() for f in self.indexed_files],
            "evidence": [e.to_dict() for e in self.evidence],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "model_prompt": self.model_prompt,
            "model_answer": self.model_answer,
            "provider_called": self.provider_called,
        }


def read_text_file(path: Optional[str]) -> str:
    if not path:
        return ""
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text(encoding="utf-8", errors="replace")


def _safe_read(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if path.stat().st_size > MAX_FILE_BYTES:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _normalize_path(text: str) -> str:
    return text.replace("\\", "/")


def parse_stacktrace(stacktrace: str, log_text: str = "") -> Tuple[str, str, List[StackFrame]]:
    text = stacktrace.strip() or log_text.strip()
    frames: List[StackFrame] = []

    # Python: File "/path/file.py", line 42, in func
    # Parse line-by-line because Python tracebacks may omit the source-code line
    # for pseudo files such as <stdin>. A regex that always consumes the next line
    # can accidentally treat the following `File ...` frame as source code and
    # lose the real failing frame.
    py_file_pattern = re.compile(r'^\s*File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>.+?)\s*$')
    text_lines = text.splitlines()
    for i, line in enumerate(text_lines):
        m = py_file_pattern.match(line)
        if not m:
            continue
        code = ""
        if i + 1 < len(text_lines):
            next_line = text_lines[i + 1]
            next_stripped = next_line.strip()
            # Source-code line is optional. Do not consume another frame, caret line,
            # or the final exception line as source code.
            if (
                next_stripped
                and not py_file_pattern.match(next_line)
                and not next_stripped.startswith("^")
                and not re.match(r'^[A-Za-z_][\w.]*?(?:Error|Exception|Fault|Failure|TypeError|KeyError|ValueError|IndexError|RuntimeError|NameError)\b', next_stripped)
            ):
                code = next_stripped
        frames.append(StackFrame(_normalize_path(m.group("file")), int(m.group("line")), m.group("func").strip(), code))

    # JS/TS: at func (/path/file.ts:42:13) or at /path/file.ts:42:13
    js_pattern = re.compile(r'\bat\s+(?:(?P<func>[\w.$<>/]+)\s+\()?((?P<file>[^()\s]+\.(?:js|ts|tsx|jsx)):(?P<line>\d+):(?P<col>\d+))\)?')
    for m in js_pattern.finditer(text):
        frames.append(StackFrame(_normalize_path(m.group("file")), int(m.group("line")), (m.group("func") or "").strip(), ""))

    # Java/Kotlin: at com.foo.Service.method(Service.java:42)
    java_pattern = re.compile(r'\bat\s+(?P<class>[\w.$]+)\.(?P<func>[\w$<>]+)\((?P<file>[^:()]+\.(?:java|kt)):(?P<line>\d+)\)')
    for m in java_pattern.finditer(text):
        frames.append(StackFrame(m.group("file"), int(m.group("line")), f"{m.group('class')}.{m.group('func')}", ""))

    # Go: /path/file.go:42 in panic stack
    go_pattern = re.compile(r'(?P<file>[^\s]+\.go):(?P<line>\d+)')
    for m in go_pattern.finditer(text):
        frames.append(StackFrame(_normalize_path(m.group("file")), int(m.group("line")), "", ""))

    # Deduplicate while preserving order
    seen = set()
    unique: List[StackFrame] = []
    for f in frames:
        key = (f.file, f.line, f.function)
        if key not in seen:
            unique.append(f)
            seen.add(key)
    frames = unique

    exception_type = "UnknownError"
    exception_message = ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Usually the last line is the exception in Python; first line often in JS/Java.
    candidates = list(reversed(lines[-8:])) + lines[:8]
    for line in candidates:
        m = re.search(r'(?P<typ>[A-Za-z_][\w.]*?(?:Error|Exception|Violation|Fault|Failure|TypeError|KeyError|ValueError|IndexError|RuntimeError|NullPointerException))\s*:?\s*(?P<msg>.*)$', line)
        if m:
            exception_type = m.group("typ").split(".")[-1]
            exception_message = m.group("msg").strip()
            break
    if exception_type == "UnknownError":
        for line in lines:
            if "error" in line.lower() or "exception" in line.lower() or "traceback" in line.lower():
                exception_message = line[:500]
                break
    return exception_type, exception_message, frames


def index_project(project_dir: Optional[str], docs_dir: Optional[str] = None) -> List[ProjectFile]:
    files: List[ProjectFile] = []
    seen_paths = set()
    roots: List[Tuple[Optional[str], str]] = [(project_dir, "code"), (docs_dir, "doc")]
    for root_value, default_kind in roots:
        if not root_value:
            continue
        root = Path(root_value).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root_value}")
        for path in root.rglob("*"):
            if len(files) >= MAX_INDEX_FILES:
                break
            if not path.is_file():
                continue
            parts = set(path.parts)
            if parts & EXCLUDED_DIRS:
                continue
            ext = path.suffix.lower()
            if ext not in CODE_EXTENSIONS and ext not in DOC_EXTENSIONS:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            resolved_path = str(path.resolve())
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)
            kind = "doc" if ext in DOC_EXTENSIONS else default_kind
            try:
                rel = str(path.relative_to(root))
            except ValueError:
                rel = path.name
            files.append(ProjectFile(str(path), _normalize_path(rel), kind, size))
    return files


def ensure_frame_files_indexed(project_dir: Optional[str], docs_dir: Optional[str], frames: Sequence[StackFrame], indexed: List[ProjectFile]) -> List[ProjectFile]:
    """Ensure stacktrace-referenced files bypass the general MAX_INDEX_FILES cap.

    Large repositories can hit the index cap before the failing file is reached.
    A user's stacktrace is high-signal input, so files referenced by frames must be
    resolved explicitly even when the broad index stopped early.
    """
    if not frames:
        return indexed
    roots = [Path(x).expanduser().resolve() for x in [project_dir, docs_dir] if x]
    existing = {str(Path(p.path).resolve()) for p in indexed}
    additions: List[ProjectFile] = []
    for frame in frames[:12]:
        frame_norm = _normalize_path(frame.file)
        frame_name = Path(frame_norm).name
        for root in roots:
            if not root.exists():
                continue
            candidates: List[Path] = []
            # Direct suffix candidate: /repo + rel path from stacktrace.
            rel_parts = [part for part in Path(frame_norm).parts if part not in {"/", "srv", "app", "tmp", "project"}]
            for i in range(len(rel_parts)):
                candidate = root.joinpath(*rel_parts[i:])
                if candidate.exists() and candidate.is_file():
                    candidates.append(candidate)
            # Fallback: basename search. This is more expensive, so do it only for stack frames.
            if not candidates:
                candidates.extend(p for p in root.rglob(frame_name) if p.is_file())
            # Prefer exact source-line match when present.
            if frame.code and candidates:
                normalized_code = " ".join(frame.code.strip().split())
                candidates.sort(key=lambda p: 0 if normalized_code and normalized_code in " ".join(_safe_read(p).split()) else 1)
            for path in candidates[:3]:
                try:
                    if path.stat().st_size > MAX_FILE_BYTES:
                        continue
                    resolved = str(path.resolve())
                    if resolved in existing:
                        continue
                    rel = str(path.relative_to(root)) if path.is_relative_to(root) else path.name
                    kind = "doc" if path.suffix.lower() in DOC_EXTENSIONS else "code"
                    additions.append(ProjectFile(str(path), _normalize_path(rel), kind, path.stat().st_size))
                    existing.add(resolved)
                    break
                except OSError:
                    continue
    return indexed + additions


def _line_window(text: str, center_line: int, radius: int = 8) -> Tuple[int, int, str]:
    lines = text.splitlines()
    if not lines:
        return 1, 1, ""
    start = max(1, center_line - radius)
    end = min(len(lines), center_line + radius)
    segment = []
    for i in range(start, end + 1):
        prefix = ">" if i == center_line else " "
        segment.append(f"{prefix}{i:04d}: {lines[i - 1]}")
    return start, end, "\n".join(segment)


def _find_matching_file(frame_file: str, indexed: Sequence[ProjectFile], frame_code: str = "") -> Optional[ProjectFile]:
    frame_norm = _normalize_path(frame_file).lower()
    frame_name = Path(frame_norm).name
    frame_code_norm = " ".join(frame_code.strip().split())

    suffix_candidates: List[ProjectFile] = []
    basename_candidates: List[ProjectFile] = []
    for pf in indexed:
        rel = pf.rel_path.lower()
        full = _normalize_path(pf.path).lower()
        if full.endswith(frame_norm) or rel.endswith(frame_norm):
            suffix_candidates.append(pf)
        if Path(pf.rel_path.lower()).name == frame_name:
            basename_candidates.append(pf)

    def code_matches(pf: ProjectFile) -> bool:
        if not frame_code_norm:
            return False
        content = _safe_read(Path(pf.path))
        normalized = " ".join(content.split())
        return frame_code_norm in normalized

    for candidates in (suffix_candidates, basename_candidates):
        if not candidates:
            continue
        # Prefer the candidate whose content contains the exact source line from stacktrace.
        for pf in candidates:
            if code_matches(pf):
                return pf
        return candidates[0]
    return None


def extract_evidence(log_text: str, stacktrace: str, frames: Sequence[StackFrame], indexed: Sequence[ProjectFile], limit: int = 18) -> List[EvidenceSnippet]:
    evidence: List[EvidenceSnippet] = []
    # Raw log/stack evidence
    if log_text.strip():
        excerpt = "\n".join(log_text.strip().splitlines()[-40:])
        evidence.append(EvidenceSnippet("log:tail", "log", 1, min(40, len(excerpt.splitlines())), excerpt, "последние строки лога", 0.95))
    if stacktrace.strip():
        evidence.append(EvidenceSnippet("stacktrace:raw", "stacktrace", 1, len(stacktrace.splitlines()), stacktrace.strip()[:12000], "исходный stacktrace", 1.0))

    # Stack referenced source windows
    for idx, frame in enumerate(frames[:8], start=1):
        pf = _find_matching_file(frame.file, indexed, frame.code)
        if not pf:
            continue
        content = _safe_read(Path(pf.path))
        start, end, snippet = _line_window(content, frame.line, radius=10)
        if snippet:
            evidence.append(EvidenceSnippet(f"code:frame:{idx}", pf.rel_path, start, end, snippet, f"файл и строка из stacktrace: {frame.function or 'unknown'}", 1.0))

    # Search tokens from exception/log/function names
    token_source = " ".join([stacktrace, log_text, " ".join(f.function for f in frames), " ".join(Path(f.file).stem for f in frames)])
    tokens = _important_tokens(token_source)
    for pf in indexed:
        if len(evidence) >= limit:
            break
        if pf.kind not in {"code", "doc"}:
            continue
        content = _safe_read(Path(pf.path))
        if not content:
            continue
        lower = content.lower()
        hit_tokens = [t for t in tokens if t.lower() in lower]
        if not hit_tokens:
            continue
        line_no = 1
        for i, line in enumerate(content.splitlines(), start=1):
            if any(t.lower() in line.lower() for t in hit_tokens):
                line_no = i
                break
        start, end, snippet = _line_window(content, line_no, radius=6)
        score = min(0.9, 0.35 + 0.08 * len(hit_tokens))
        evidence.append(EvidenceSnippet(f"search:{len(evidence)+1}", pf.rel_path, start, end, snippet, "поиск по токенам: " + ", ".join(hit_tokens[:8]), score))

    return evidence[:limit]


def _important_tokens(text: str, limit: int = 30) -> List[str]:
    raw = re.findall(r"[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]{2,}", text)
    stop = {
        "file", "line", "traceback", "error", "exception", "null", "none", "undefined", "true", "false",
        "and", "the", "for", "with", "from", "self", "this", "return", "call", "args", "kwargs",
        "ошибка", "исключение", "строка", "файл", "пользователь", "клиент", "сервис",
    }
    counts: Dict[str, int] = {}
    for token in raw:
        key = token.strip("_")
        if len(key) < 3 or key.lower() in stop:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:limit]]


def build_hypotheses(exception_type: str, exception_message: str, frames: Sequence[StackFrame], evidence: Sequence[EvidenceSnippet]) -> List[BugHypothesis]:
    lower = f"{exception_type} {exception_message}".lower()
    top_refs = [e.ref for e in evidence[:5]]
    suspected = _suspected_location(frames, evidence)
    hypotheses: List[BugHypothesis] = []

    if "nonetype" in lower or "none" in lower or "nullpointer" in lower or "undefined" in lower or "has no attribute" in lower or "not subscriptable" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, nullable-значение используется как объект/словарь без проверки",
            confidence=0.78 if evidence else 0.62,
            evidence_refs=top_refs,
            explanation=(
                f"Исключение `{exception_type}: {exception_message}` обычно означает, что upstream-функция вернула None/null/undefined, "
                f"а код в {suspected} обращается к полю, индексу или методу без guard-проверки."
            ),
            verification_steps=[
                "Проверить переменные на строке падения и функции, которые их заполняют.",
                "Воспроизвести кейс с отсутствующей записью/пустым ответом внешнего сервиса.",
                "Добавить временный лог значения перед строкой падения и correlationId запроса.",
            ],
            fix_plan=[
                "Добавить явную проверку None/null/undefined до обращения к полям.",
                "Развести сценарии: данные найдены / данные отсутствуют / внешний сервис вернул пустой ответ.",
                "Вернуть понятную доменную ошибку вместо технического TypeError/NullPointerException.",
                "Добавить regression test на пустой результат upstream-функции.",
            ],
            risk="high",
        ))
    if "keyerror" in lower or re.search(r"missing key|key not found|no such key", lower):
        hypotheses.append(BugHypothesis(
            title="Вероятно, drift контракта: код ждёт ключ, которого нет во входных данных",
            confidence=0.74,
            evidence_refs=top_refs,
            explanation="KeyError обычно появляется при рассинхронизации JSON/словаря/DTO: producer не прислал поле, consumer не обработал отсутствие.",
            verification_steps=["Сравнить payload из лога с DTO/схемой.", "Проверить release/версию producer'а и consumer'а."],
            fix_plan=["Добавить schema validation на границе.", "Задать default/optional handling или миграцию контракта.", "Добавить тест на payload без ключа."],
            risk="high",
        ))
    if "indexerror" in lower or "out of range" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, код обращается к первому/последнему элементу пустой коллекции",
            confidence=0.70,
            evidence_refs=top_refs,
            explanation="IndexError часто связан с отсутствием данных при ожидании минимум одного элемента.",
            verification_steps=["Проверить размер коллекции перед строкой падения.", "Воспроизвести кейс с пустым результатом поиска."],
            fix_plan=["Добавить guard для пустой коллекции.", "Вернуть доменную ошибку/empty result.", "Покрыть тестом пустую коллекцию."],
            risk="medium",
        ))
    if "jsondecode" in lower or "parse" in lower or "invalid literal" in lower or "valueerror" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, формат входных данных не соответствует ожидаемому парсеру",
            confidence=0.66,
            evidence_refs=top_refs,
            explanation="Ошибка парсинга обычно указывает на пустой/битый JSON, неожиданный формат числа/даты или HTML вместо JSON.",
            verification_steps=["Сохранить raw response/input из лога.", "Проверить Content-Type, encoding и формат полей."],
            fix_plan=["Добавить предварительную валидацию формата.", "Разделить ошибки внешнего сервиса и ошибки бизнес-валидации.", "Добавить тесты на битый/пустой input."],
            risk="medium",
        ))
    if "timeout" in lower or "connection" in lower or "connect" in lower or "503" in lower or "502" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, отказ внешней зависимости или неправильная timeout/retry политика",
            confidence=0.64,
            evidence_refs=top_refs,
            explanation="Сетевые/timeout ошибки редко чинятся только в месте падения: нужно смотреть dependency, retry, circuit breaker и идемпотентность.",
            verification_steps=["Проверить метрики зависимости за время инцидента.", "Проверить retry storm и лимиты пула соединений."],
            fix_plan=["Настроить timeout/retry/circuit breaker.", "Сделать безопасную деградацию и DLQ/manual review для бизнес-операции.", "Добавить алерты по dependency error rate."],
            risk="high",
        ))
    if "integrity" in lower or "unique" in lower or "not null" in lower or "constraint" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, нарушен контракт данных или идемпотентность на уровне БД",
            confidence=0.68,
            evidence_refs=top_refs,
            explanation="DB constraint ошибки часто означают дубль команды, отсутствующее обязательное поле или рассинхрон доменных правил и схемы БД.",
            verification_steps=["Проверить SQL/таблицу/constraint из лога.", "Найти повторные correlationId/idempotencyKey."],
            fix_plan=["Исправить маппинг обязательных полей.", "Добавить idempotency guard.", "Вернуть доменную ошибку вместо 500."],
            risk="high",
        ))

    if "nameerror" in lower or "not defined" in lower or "is not defined" in lower:
        missing_match = re.search(r"name ['\"]?(?P<name>[A-Za-z_][\w]*)['\"]? is not defined", exception_message)
        missing_name = missing_match.group("name") if missing_match else "символ"
        # Prefer symbols used on the exact stacktrace source line/window. Broader search
        # snippets may contain unrelated typing imports from other files and would make
        # the suggested fix noisy.
        frame_text = "\n".join(e.text for e in evidence if e.ref.startswith("code:frame"))
        evidence_text = frame_text or "\n".join(e.text for e in evidence[:3])
        typing_names = [name for name in ["Optional", "List", "Dict", "Tuple", "Any", "Sequence", "Mapping"] if name in evidence_text or name == missing_name]
        typing_fix = "from typing import " + ", ".join(dict.fromkeys(typing_names)) if typing_names else "добавить отсутствующий import/объявление символа"
        hypotheses.append(BugHypothesis(
            title="Вероятно, используется символ без импорта или объявления",
            confidence=0.78 if evidence else 0.60,
            evidence_refs=top_refs,
            explanation=(
                f"Исключение `{exception_type}: {exception_message}` означает, что интерпретатор дошёл до имени `{missing_name}`, "
                "но оно не определено в области видимости. Чаще всего это забытый import, опечатка или несовместимость версии Python/typing."
            ),
            verification_steps=[
                f"Открыть failing line и проверить, где используется `{missing_name}`.",
                "Проверить import-блок этого файла и наличие нужного символа в runtime-версии Python.",
                "Запустить минимальный import модуля, чтобы подтвердить, что ошибка возникает до бизнес-логики.",
            ],
            fix_plan=[
                typing_fix + ".",
                "Добавить smoke test на импорт CLI/модуля.",
                "Запустить compileall/unit tests, чтобы поймать такие ошибки до релиза.",
            ],
            risk="medium",
        ))

    if "modulenotfound" in lower or "importerror" in lower or "no module named" in lower:
        module_match = re.search(r"no module named ['\"](?P<module>[^'\"]+)['\"]", exception_message, re.I)
        module_name = module_match.group("module") if module_match else "missing module"
        hypotheses.append(BugHypothesis(
            title="Вероятно, отсутствует runtime-зависимость или import-путь",
            confidence=0.82 if evidence else 0.62,
            evidence_refs=top_refs,
            explanation=f"Исключение `{exception_type}: {exception_message}` означает, что Python не смог импортировать `{module_name}`. Обычно причина в requirements/pyproject, окружении контейнера или неправильном PYTHONPATH.",
            verification_steps=["Проверить requirements/pyproject/lock-файл и Docker image.", f"Запустить минимальный import `{module_name}` в том же окружении.", "Сравнить dev/prod зависимости и переменные PYTHONPATH."],
            fix_plan=["Добавить отсутствующую dependency в requirements/pyproject и пересобрать lock/image.", "Если это локальный модуль — исправить package/import path.", "Добавить smoke test на импорт модуля при старте."],
            risk="high",
        ))

    if "uuid" in lower or "badly formed hexadecimal" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, входной идентификатор не соответствует UUID-формату",
            confidence=0.72 if evidence else 0.55,
            evidence_refs=top_refs,
            explanation="Строка ошибки указывает, что parser UUID получил значение не в UUID-формате. Это validation/contract bug, если клиент может отправлять временные numeric ids.",
            verification_steps=["Посмотреть raw id из request/log.", "Сверить контракт API: UUID vs numeric/temp id.", "Проверить, должен ли сервис вернуть 400 INVALID_ID вместо 500."],
            fix_plan=["Добавить явную validation boundary перед UUID(...).", "Вернуть доменную/HTTP 400 ошибку INVALID_ID.", "Добавить regression test на numeric/bad UUID."],
            risk="medium",
        ))

    if "numberformatexception" in lower or "for input string" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, числовой парсер не поддерживает фактический формат входа",
            confidence=0.70 if evidence else 0.50,
            evidence_refs=top_refs,
            explanation="NumberFormatException часто означает, что код ждёт integer, а получает decimal/string в другом формате. Для денежных значений нужен Decimal/BigDecimal, не Integer.parseInt.",
            verification_steps=["Проверить raw value из лога.", "Сверить контракт поля: integer, decimal, string.", "Проверить локаль и decimal separator."],
            fix_plan=["Использовать BigDecimal/Decimal или явную валидацию формата.", "Вернуть понятную validation error.", "Добавить regression test на decimal amount вроде 10.50."],
            risk="medium",
        ))

    if "connection refused" in lower or "localhost" in lower:
        hypotheses.append(BugHypothesis(
            title="Вероятно, неверная runtime-конфигурация адреса зависимости",
            confidence=0.70 if evidence else 0.50,
            evidence_refs=top_refs,
            explanation="Connection refused на localhost в контейнере/проде часто означает, что сервис использует default/local host вместо production host из config/env.",
            verification_steps=["Проверить env/config для host/port зависимости в том же окружении.", "Проверить, не подставился ли default localhost.", "Сравнить deploy docs и фактический config dump."],
            fix_plan=["Исправить host/port в config/env/secrets.", "Запретить небезопасный default localhost для prod.", "Добавить smoke check конфигурации при старте."],
            risk="high",
        ))

    if not hypotheses:
        hypotheses.append(BugHypothesis(
            title="Причина неочевидна: нужен model-assisted анализ по evidence bundle",
            confidence=0.42 if evidence else 0.25,
            evidence_refs=top_refs,
            explanation=(
                f"По строке ошибки `{exception_type}: {exception_message}` нельзя надёжно назвать root cause. "
                "CogProxy собрал stacktrace, подозрительные файлы и контекст для модели."
            ),
            verification_steps=["Запустить с реальным --provider-cmd.", "Добавить полный лог, конфиг окружения и шаги воспроизведения."],
            fix_plan=["Сначала подтвердить failing line и входные данные.", "Потом исправлять минимально по подтверждённой гипотезе, не переписывая весь модуль."],
            risk="medium",
        ))
    return hypotheses[:5]


def _suspected_location(frames: Sequence[StackFrame], evidence: Sequence[EvidenceSnippet]) -> str:
    if frames:
        f = frames[-1]
        return f"{Path(f.file).name}:{f.line}" if f.line else Path(f.file).name
    for e in evidence:
        if e.file not in {"log", "stacktrace"}:
            return f"{e.file}:{e.start_line}-{e.end_line}"
    return "подозрительной строке из stacktrace"


def build_model_prompt(contract: TaskContract, log_text: str, stacktrace: str, exception_type: str, exception_message: str, frames: Sequence[StackFrame], evidence: Sequence[EvidenceSnippet], hypotheses: Sequence[BugHypothesis]) -> str:
    evidence_lines = []
    for ev in evidence[:12]:
        evidence_lines.append(f"### {ev.ref} | {ev.file}:{ev.start_line}-{ev.end_line} | {ev.reason}\n{ev.text[:4000]}")
    hypothesis_lines = [f"- {h.title} (confidence={h.confidence}): {h.explanation}" for h in hypotheses]
    frame_lines = [f"- {f.file}:{f.line} in {f.function} | {f.code}" for f in frames[:12]]
    return (
        "Ты senior debugging assistant внутри CogProxy DQE. Твоя задача — не дать общие советы, а найти наиболее вероятную причину бага в проекте.\n"
        "Работай строго по evidence: log, stacktrace, snippets кода, документация. Если доказательств мало — явно скажи, что гипотеза не подтверждена.\n\n"
        f"Задача пользователя: {contract.goal}\n"
        f"Exception: {exception_type}: {exception_message}\n\n"
        "## Stack frames\n" + ("\n".join(frame_lines) if frame_lines else "нет распознанных frames") + "\n\n"
        "## Offline hypotheses from CogProxy\n" + ("\n".join(hypothesis_lines) if hypothesis_lines else "нет") + "\n\n"
        "## Evidence bundle\n" + "\n\n".join(evidence_lines) + "\n\n"
        "Сформируй ответ по структуре:\n"
        "1. Наиболее вероятная причина\n"
        "2. Цепочка доказательств log → stacktrace → code/docs\n"
        "3. Альтернативные гипотезы\n"
        "4. Как проверить за 15 минут\n"
        "5. Минимальный fix\n"
        "6. Regression tests\n"
    )


def render_bug_report(contract: TaskContract, exception_type: str, exception_message: str, frames: Sequence[StackFrame], evidence: Sequence[EvidenceSnippet], hypotheses: Sequence[BugHypothesis], model_answer: Optional[str], provider_called: bool, indexed_files: Sequence[ProjectFile]) -> str:
    top = hypotheses[0] if hypotheses else None
    suspected_files = []
    for ev in evidence:
        if ev.file not in {"log", "stacktrace"} and ev.file not in suspected_files:
            suspected_files.append(ev.file)
    lines = [
        "# Ответ DQE",
        "",
        "## Итог",
    ]
    if top:
        lines.append(f"Наиболее вероятная причина: **{top.title}**.")
        lines.append(f"Confidence offline-анализа: **{top.confidence:.2f}**. Это гипотеза, пока её не подтвердили запуском/тестом.")
    else:
        lines.append("Причина не определена: данных мало.")
    lines += [
        "",
        "## Что известно из лога и stacktrace",
        f"- Exception: `{exception_type}: {exception_message}`",
        f"- Распознано frames: {len(frames)}",
        f"- Проиндексировано файлов кода/документации: {len(indexed_files)}",
    ]
    if frames:
        lines.append("- Последний frame: `" + f"{frames[-1].file}:{frames[-1].line} in {frames[-1].function}" + "`")
    if suspected_files:
        lines.append("- Подозрительные файлы: " + ", ".join(f"`{f}`" for f in suspected_files[:8]))

    lines += ["", "## Цепочка доказательств"]
    if evidence:
        for ev in evidence[:10]:
            lines.append(f"- **{ev.ref}** — `{ev.file}:{ev.start_line}-{ev.end_line}`: {ev.reason}")
    else:
        lines.append("- Evidence не собран: передайте `--project-dir`, `--log-file` и `--stacktrace-file`.")

    lines += ["", "## Гипотезы root cause"]
    for i, h in enumerate(hypotheses, start=1):
        lines.append(f"### H{i}. {h.title}")
        lines.append(f"- Confidence: {h.confidence:.2f}")
        lines.append(f"- Evidence: {', '.join(h.evidence_refs) if h.evidence_refs else 'нет'}")
        lines.append(f"- Объяснение: {h.explanation}")
        lines.append("- Как проверить:")
        lines.extend(f"  - {x}" for x in h.verification_steps)
        lines.append("- Минимальный fix:")
        lines.extend(f"  - {x}" for x in h.fix_plan)

    lines += ["", "## Snippets кода и документации"]
    for ev in evidence:
        if ev.file in {"log", "stacktrace"}:
            continue
        lines.append(f"### {ev.ref} — {ev.file}:{ev.start_line}-{ev.end_line}")
        lines.append("```text")
        lines.append(ev.text[:4000])
        lines.append("```")

    lines += ["", "## Взаимодействие с моделью"]
    if provider_called and model_answer:
        lines.append("Внешняя CLI-модель была вызвана. Её ответ ниже не принят как истина автоматически; его надо сверять с evidence.")
        lines.append("\n### Ответ модели\n")
        lines.append(model_answer.strip())
    else:
        lines.append("Внешняя модель не вызывалась. Это offline-анализ: он помогает сузить место и подготовить prompt, но не гарантирует root cause.")

    lines += ["", "## Что ещё нужно от клиента"]
    lines.extend([
        "- Полный лог с correlationId/requestId за одну операцию.",
        "- Версия сервиса/коммита, окружение, конфиг feature flags.",
        "- Минимальные шаги воспроизведения или payload запроса.",
        "- Если есть внешняя зависимость — её ответ/код статуса на момент ошибки.",
    ])
    return "\n".join(lines).strip() + "\n"


def run_bug_analysis(contract: TaskContract, provider: BaseProvider) -> WorkerResult:
    meta = contract.metadata
    log_text = meta.get("log_text") or read_text_file(meta.get("log_file"))
    stacktrace = meta.get("stacktrace_text") or read_text_file(meta.get("stacktrace_file"))
    if not stacktrace and "traceback" in contract.source_text.lower():
        stacktrace = contract.source_text
    if not log_text and contract.source_text:
        log_text = contract.source_text

    exception_type, exception_message, frames = parse_stacktrace(stacktrace, log_text)
    indexed = ensure_frame_files_indexed(meta.get("project_dir"), meta.get("docs_dir"), frames, index_project(meta.get("project_dir"), meta.get("docs_dir")))
    evidence = extract_evidence(log_text, stacktrace, frames, indexed)
    hypotheses = build_hypotheses(exception_type, exception_message, frames, evidence)
    prompt = build_model_prompt(contract, log_text, stacktrace, exception_type, exception_message, frames, evidence, hypotheses)

    provider_called = False
    model_answer: Optional[str] = None
    if not isinstance(provider, DeterministicProvider):
        try:
            model_answer = provider.complete(prompt, role="bug_root_cause")
            provider_called = True
        except ProviderError as exc:
            model_answer = f"Provider error: {exc}"
            provider_called = False

    report = render_bug_report(contract, exception_type, exception_message, frames, evidence, hypotheses, model_answer, provider_called, indexed)
    result = BugAnalysisResult(
        exception_type=exception_type,
        exception_message=exception_message,
        frames=list(frames),
        indexed_files=indexed,
        evidence=evidence,
        hypotheses=hypotheses,
        model_prompt=prompt,
        model_answer=model_answer,
        provider_called=provider_called,
        report=report,
    )
    return WorkerResult(
        worker_name="bug_analyzer",
        role="bug_analysis",
        content=report,
        artifacts={
            "bug_analysis": result.to_dict(),
            "bug_report": report,
            "bug_evidence": [e.to_dict() for e in evidence],
            "llm_prompt": prompt,
            "model_analysis": model_answer,
        },
        confidence=0.78 if evidence else 0.45,
        used_provider=provider_called,
    )
