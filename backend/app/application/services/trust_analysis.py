"""Trust and execution risk analysis service.

This module provides a modular plugin-based engine for detecting
repository-level risks that could compromise a user's machine when
interacting with the repository (cloning, building, installing dependencies,
opening in IDE, etc.).

Each detector is a callable that scans the repository (without executing code)
and returns a list of findings. Findings are aggregated and scored to produce
a trust risk score (0-100, where lower is riskier).

The service can be used similarly to the existing findings scan for bugs and
security, but focuses on trust and execution risk.
"""
from __future__ import annotations

import os
import re
from typing import Callable, List, Tuple

from app.domain.enums import Severity

# Type alias for a detector function.
Detector = Callable[[str], List[dict]]  # repo_path -> list of finding dicts


class TrustAnalysisService:
    """Orchestrates trust and risk detectors."""

    def __init__(self) -> None:
        self._detectors: List[Detector] = self._build_detectors()

    def _build_detectors(self) -> List[Detector]:
        """Return list of detector functions."""
        return [
            detect_git_hooks,
            detect_core_hooks_path,
            detect_git_filters,
            detect_git_lfs_filters,
            detect_gitmodules_submodules,
            detect_hidden_files,
            detect_newly_introduced_executables,
            detect_encoded_payloads,
            detect_dynamic_code_execution,
            detect_shell_scripts,
            detect_powershell_scripts,
            detect_scheduled_tasks,
            detect_registry_persistence,
            detect_startup_folder,
            detect_credential_theft_patterns,
            detect_ssh_key_access,
            detect_browser_cookie_theft,
            detect_env_harvesting,
            detect_dotenv_harvesting,
            detect_cloud_credential_access,
            detect_crypto_wallet_access,
            detect_network_exfiltration,
        ]

    def run(self, repo_path: str) -> tuple[dict, dict, int]:
        """Run all detectors and return summary, metrics, and score.

        Returns:
            tuple: (summary dict, metrics dict, score int 0-100)
        """
        all_findings: List[dict] = []
        for detector in self._detectors:
            try:
                findings = detector(repo_path)
                all_findings.extend(findings)
            except Exception:
                # Continue even if one detector fails
                continue

        # Deduplicate findings by (file_path, line, title)
        seen: set[Tuple[str, int, str]] = set()
        unique_findings: List[dict] = []
        for f in all_findings:
            key = (f.get("file_path", ""), f.get("line", 0), f.get("title", ""))
            if key not in seen:
                seen.add(key)
                unique_findings.append(f)

        # Count by severity
        from app.domain.enums import Severity

        counts = {s.value: 0 for s in Severity}
        for f in unique_findings:
            sev = f.get("severity")
            if sev in counts:
                counts[sev] += 1

        # Compute score using same penalty weights as other findings scans
        _SEVERITY_PENALTY: dict[str, int] = {
            Severity.CRITICAL.value: 25,
            Severity.HIGH.value: 15,
            Severity.MEDIUM.value: 8,
            Severity.LOW.value: 3,
            Severity.INFO.value: 1,
        }
        penalty = sum(_SEVERITY_PENALTY.get(sev, 0) * n for sev, n in counts.items())
        score = max(0, 100 - penalty)

        # Overview
        total = len(unique_findings)
        if total == 0:
            overview = "No suspicious indicators detected."
        else:
            overview = f"Found {total} potential security/risk indicators."

        summary = {
            "overview": overview,
            "findings": unique_findings,
        }
        metrics = {
            "counts": counts,
            "total_findings": total,
        }

        return summary, metrics, score


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #


def _make_finding(
    *,
    title: str,
    category: str,
    severity: Severity,
    file_path: str,
    line: int,
    description: str,
    recommendation: str,
) -> dict:
    """Create a finding dictionary consistent with the findings scan schema."""
    return {
        "title": title,
        "category": category,
        "severity": severity.value,
        "file_path": file_path,
        "line": line,
        "description": description,
        "recommendation": recommendation,
    }


def _read_lines(file_path: str) -> List[str]:
    """Read lines from a file, returning empty list on error."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except OSError:
        return []


def _is_binary_file(file_path: str) -> bool:
    """Heuristic to check if a file is binary."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except OSError:
        return True  # treat as binary to be safe


# --------------------------------------------------------------------------- #
# Detectors
# --------------------------------------------------------------------------- #


def detect_git_hooks(repo_path: str) -> List[dict]:
    """Detect Git hooks that could execute on clone/checkout/etc."""
    findings: List[dict] = []
    hooks_dir = os.path.join(repo_path, ".git", "hooks")
    if not os.path.isdir(hooks_dir):
        return findings

    hook_names = [
        "applypatch-msg",
        "pre-applypatch",
        "post-applypatch",
        "pre-commit",
        "prepare-commit-msg",
        "commit-msg",
        "post-commit",
        "pre-rebase",
        "post-checkout",
        "post-merge",
        "pre-receive",
        "update",
        "post-receive",
        "push-to-checkout",
        "pre-auto-gc",
        "post-merge",
        "pre-push",
        "reference-transaction",
    ]

    for hook in hook_names:
        hook_path = os.path.join(hooks_dir, hook)
        if os.path.isfile(hook_path) and os.access(hook_path, os.X_OK):
            findings.append(
                _make_finding(
                    title=f"Executable Git hook: {hook}",
                    category="Git Hooks",
                    severity=Severity.HIGH,
                    file_path=hook_path,
                    line=1,
                    description=f"The Git hook '{hook}' is executable and could run during git operations.",
                    recommendation="Review the hook script for malicious code. Consider disabling Git hooks if untrusted.",
                )
            )
        elif os.path.isfile(hook_path):
            findings.append(
                _make_finding(
                    title=f"Git hook present: {hook}",
                    category="Git Hooks",
                    severity=Severity.LOW,
                    file_path=hook_path,
                    line=1,
                    description=f"The Git hook '{hook}' exists (non-executable). Could be made executable later.",
                    recommendation="Review the hook content.",
                )
            )
    return findings


def detect_core_hooks_path(repo_path: str) -> List[dict]:
    """Detect attempts to modify core.hooksPath via git config or command."""
    findings: List[dict] = []
    config_path = os.path.join(repo_path, ".git", "config")
    if os.path.isfile(config_path):
        lines = _read_lines(config_path)
        for i, line in enumerate(lines, start=1):
            if "core.hooksPath" in line.lower():
                findings.append(
                    _make_finding(
                        title="core.hooksPath configured in .git/config",
                        category="Git Config",
                        severity=Severity.HIGH,
                        file_path=config_path,
                        line=i,
                        description="The repository's .git/config sets core.hooksPath, which could redirect hooks to attacker-controlled directories.",
                        recommendation="Remove or inspect the core.hooksPath setting.",
                    )
                )
    return findings


def detect_git_filters(repo_path: str) -> List[dict]:
    """Detect Git filter (clean/smudge) configurations in .gitattributes or .git/config."""
    findings: List[dict] = []
    gitattributes = os.path.join(repo_path, ".gitattributes")
    if os.path.isfile(gitattributes):
        lines = _read_lines(gitattributes)
        for i, line in enumerate(lines, start=1):
            if "filter=" in line.lower():
                findings.append(
                    _make_finding(
                        title="Git filter defined in .gitattributes",
                        category="Git Attributes",
                        severity=Severity.MEDIUM,
                        file_path=gitattributes,
                        line=i,
                        description=".gitattributes defines a filter (clean/smudge) that runs on checkout/commit.",
                        recommendation="Inspect the filter commands for malicious intent.",
                    )
                )
    config_path = os.path.join(repo_path, ".git", "config")
    if os.path.isfile(config_path):
        lines = _read_lines(config_path)
        for i, line in enumerate(lines, start=1):
            if "filter." in line.lower():
                findings.append(
                    _make_finding(
                        title="Git filter configured in .git/config",
                        category="Git Config",
                        severity=Severity.MEDIUM,
                        file_path=config_path,
                        line=i,
                        description=".git/config defines a filter that could execute arbitrary code.",
                        recommendation="Review filter definitions.",
                    )
                )
    return findings


def detect_git_lfs_filters(repo_path: str) -> List[dict]:
    """Detect Git LFS filter processes that could be malicious."""
    findings: List[dict] = []
    gitattributes = os.path.join(repo_path, ".gitattributes")
    if os.path.isfile(gitattributes):
        lines = _read_lines(gitattributes)
        for i, line in enumerate(lines, start=1):
            if "filter=lfs" in line.lower():
                findings.append(
                    _make_finding(
                        title="Git LFS filter detected",
                        category="Git LFS",
                        severity=Severity.LOW,
                        file_path=gitattributes,
                        line=i,
                        description=".gitattributes specifies filter=lfs, which invokes Git LFS clean/smudge filters.",
                        recommendation="Ensure Git Lfs is from a trusted source; consider disabling if not needed.",
                    )
                )
    return findings


def detect_gitmodules_submodules(repo_path: str) -> List[dict]:
    """Check for suspicious submodules in .gitmodules."""
    findings: List[dict] = []
    gitmodules_path = os.path.join(repo_path, ".gitmodules")
    if os.path.isfile(gitmodules_path):
        try:
            import configparser

            config = configparser.ConfigParser()
            config.read(gitmodules_path)
            for section in config.sections():
                if section.startswith('submodule "'):
                    url = config.get(section, "url", fallback="")
                    if url:
                        findings.append(
                            _make_finding(
                                title=f"Submodule detected: {section}",
                                category="Git Submodules",
                                severity=Severity.MEDIUM,
                                file_path=gitmodules_path,
                                line=0,
                                description=f"Submodule '{section}' points to external repository: {url}",
                                recommendation="Review the submodule source for trustworthiness.",
                            )
                        )
        except Exception:
            findings.append(
                _make_finding(
                    title=".gitmodules file present",
                    category="Git Submodules",
                    severity=Severity.LOW,
                    file_path=gitmodules_path,
                    line=1,
                    description=".gitmodules file indicates the repository uses submodules.",
                    recommendation="Inspect .gitmodules for untrusted submodule sources.",
                )
            )
    return findings


def detect_hidden_files(repo_path: str) -> List[dict]:
    """Detect hidden files and directories that might be obscured."""
    findings: List[dict] = []
    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory to reduce noise
        if "/.git/" in root.replace("\\", "/"):
            dirs[:] = []
            continue
        for name in dirs + files:
            if name.startswith(".") and name not in {".", ".."}:
                full = os.path.join(root, name)
                is_dir = os.path.isdir(full)
                rel_path = os.path.relpath(full, repo_path)
                findings.append(
                    _make_finding(
                        title=f"{'Directory' if is_dir else 'File'} with hidden name: {name}",
                        category="Hidden Files",
                        severity=Severity.LOW,
                        file_path=rel_path,
                        line=0,
                        description=f"Hidden {'directory' if is_dir else 'file'} may be used to conceal malicious content.",
                        recommendation="Review the contents of this hidden item.",
                    )
                )
    return findings


def detect_newly_introduced_executables(repo_path: str) -> List[dict]:
    """Detect executable files that are not typically expected."""
    findings: List[dict] = []
    exe_extensions = {".exe", ".bin", ".run", ".out", ".app"}
    script_extensions = {".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd", ".vbs", ".js", ".py", ".rb", ".pl"}
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_path)
            _, ext = os.path.splitext(file)
            ext_lower = ext.lower()

            try:
                mode = os.stat(full_path).st_mode
                is_executable = bool(mode & (os.X_OK | os.S_IXUSR | os.S_IXGRP | os.S_IXOTH))
            except OSError:
                continue

            if is_executable:
                lower_rel = rel_path.lower()
                if any(
                    lower_rel.startswith(prefix)
                    for prefix in [
                        ".github/workflows/",
                        ".gitlab-ci/",
                        ".circleci/",
                        "azure-pipelines/",
                        ".jenkins/",
                    ]
                ):
                    severity = Severity.LOW
                    category = "CI Configuration"
                else:
                    severity = Severity.MEDIUM
                    category = "Executable File"

                findings.append(
                    _make_finding(
                        title=f"Executable file: {file}",
                        category=category,
                        severity=severity,
                        file_path=rel_path,
                        line=0,
                        description=f"Executable file '{file}' found with permission bits set.",
                        recommendation="Verify the purpose of this executable. Ensure it is not malicious.",
                    )
                )
            elif ext_lower in script_extensions:
                findings.append(
                    _make_finding(
                        title=f"Script file: {file}",
                        category="Script File",
                        severity=Severity.LOW,
                        file_path=rel_path,
                        line=0,
                        description=f"Script file with extension {ext} found. Could be executed if permissions changed.",
                        recommendation="Review script content for harmful behavior.",
                    )
                )
    return findings


def detect_encoded_payloads(repo_path: str) -> List[dict]:
    """Detect base64, hex, or other encoded strings that might hide payloads."""
    findings: List[dict] = []
    base64_pattern = re.compile(r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?')
    hex_pattern = re.compile(r'\b[0-9a-fA-F]{8,}\b')
    gzip_b64_marker = re.compile(r'H4sI')

    for root, dirs, files in os.walk(repo_path):
        from app.core.constants import IGNORED_DIRS

        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for match in base64_pattern.finditer(line):
                    matched = match.group(0)
                    if len(matched) >= 20 and re.match(r'^[A-Za-z0-9+/]+=*$', matched):
                        findings.append(
                            _make_finding(
                                title="Potential base64-encoded payload",
                                category="Obfuscation",
                                severity=Severity.MEDIUM,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Long base64 string detected (length {len(matched)}). May encode executable code.",
                                recommendation="Investigate the purpose of this encoded string.",
                            )
                        )
                for match in hex_pattern.finditer(line):
                    matched = match.group(0)
                    if len(matched) >= 16:
                        findings.append(
                            _make_finding(
                                title="Potential hex-encoded payload",
                                category="Obfuscation",
                                severity=Severity.MEDIUM,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Long hex string detected (length {len(matched)}). May encode binary data.",
                                recommendation="Examine this hex string; it could be shellcode or binary payload.",
                            )
                        )
                if gzip_b64_marker.search(line):
                    findings.append(
                        _make_finding(
                            title="Potential gzip+base64 encoded payload",
                            category="Obfuscation",
                            severity=Severity.MEDIUM,
                            file_path=os.path.relpath(full_path, repo_path),
                            line=i,
                            description="String appears to be a gzip-compressed base64 payload (starts with H4sI).",
                            recommendation="This may conceal a payload; decode and inspect.",
                        )
                    )
    return findings


def detect_dynamic_code_execution(repo_path: str) -> List[dict]:
    """Detect patterns like eval, exec, compile, etc. in various languages."""
    findings: List[dict] = []
    patterns = [
        (r'\beval\s*\(', "eval", ".py", "Python"),
        (r'\bexec\s*\(', "exec", ".py", "Python"),
        (r'\bcompile\s*\(', "compile", ".py", "Python"),
        (r'__import__\s*\(', "__import__", ".py", "Python"),
        (r'\beval\s*\(', "eval", ".js", "JavaScript"),
        (r'\beval\s*\(', "eval", ".ts", "TypeScript"),
        (r'\bnew\s+Function\s*\(', "Function constructor", ".js", "JavaScript"),
        (r'\bnew\s+Function\s*\(', "Function constructor", ".ts", "TypeScript"),
        (r'\beval\s*\(', "eval", ".php", "PHP"),
        (r'\bassert\s*\(', "assert", ".php", "PHP"),
        (r'\beval\s*\(', "eval", ".rb", "Ruby"),
        (r'\binstance_eval\s*\(', "instance_eval", ".rb", "Ruby"),
    ]

    for root, dirs, files in os.walk(repo_path):
        from app.core.constants import IGNORED_DIRS

        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            ext = os.path.splitext(file)[1].lower()
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, keyword, ext_lang, lang in patterns:
                    if ext_lang == ext or (ext_lang in [".js", ".ts"] and ext in [".js", ".ts"]):
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append(
                                _make_finding(
                                    title=f"Potential dangerous function: {keyword}",
                                    category="Dynamic Code Execution",
                                    severity=Severity.HIGH,
                                    file_path=os.path.relpath(full_path, repo_path),
                                    line=i,
                                    description=f"Use of '{keyword}' found in {lang} code. Can execute arbitrary code.",
                                    recommendation="Avoid using eval-like functions. If necessary, sanitize inputs strictly.",
                                )
                            )
    return findings


def detect_shell_scripts(repo_path: str) -> List[dict]:
    """Detect shell scripts (bash, sh, etc.) that might contain harmful commands."""
    findings: List[dict] = []
    script_extensions = {".sh", ".bash", ".zsh", ".fish"}
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in script_extensions:
                full_path = os.path.join(root, file)
                lines = _read_lines(full_path)
                if not lines:
                    continue
                dangerous_patterns = [
                    (r'\brm\s+-rf\s+/', "rm -f /", "destructive"),
                    (r'\bdd\s+if=.*of=/dev/sd', "dd overwriting disk", "data destruction"),
                    (r'\b>:\(\)\{ \|\:&\};:', "fork bomb", "DoS"),
                    (r'\bwget\s+http[s]?://.*\|\s*bash\b', "wget pipe to bash", "download and execute"),
                    (r'\bcurl\s+http[s]?://.*\|\s*bash\b', "curl pipe to bash", "download and execute"),
                    (r'\bchmod\s+\+x.*\$0', "self-modifying", "self-modifying script"),
                ]
                for i, line in enumerate(lines, start=1):
                    for pattern, description, _ in dangerous_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append(
                                _make_finding(
                                    title=f"Potentially dangerous shell command: {description}",
                                    category="Shell Script",
                                    severity=Severity.HIGH,
                                    file_path=os.path.relpath(full_path, repo_path),
                                    line=i,
                                    description=f"Line contains pattern indicative of {description}.",
                                    recommendation="Review this script for malicious intent.",
                                )
                            )
    return findings


def detect_powershell_scripts(repo_path: str) -> List[dict]:
    """Detect PowerShell scripts with potentially harmful commands."""
    findings: List[dict] = []
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            if file.lower().endswith(".ps1"):
                full_path = os.path.join(root, file)
                lines = _read_lines(full_path)
                if not lines:
                    continue
                suspicious = [
                    (r'\bIEX\s+', "Invoke-Expression (IEX)", "code injection"),
                    (r'\bInvoke-Expression\s+', "Invoke-Expression", "code injection"),
                    (r'\bStart-Process\s+', "Start-Process", "process execution"),
                    (r'\bDownloadString\s+', "DownloadString", "download and execute"),
                    (r'\bInvoke-WebRequest\s+.*-\s*OutFile', "Invoke-WebRequest to file", "download file"),
                ]
                for i, line in enumerate(lines, start=1):
                    for pattern, name, _ in suspicious:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append(
                                _make_finding(
                                    title=f"Potentially dangerous PowerShell: {name}",
                                    category="PowerShell",
                                    severity=Severity.HIGH,
                                    file_path=os.path.relpath(full_path, repo_path),
                                    line=i,
                                    description=f"PowerShell contains {name} which can execute arbitrary code.",
                                    recommendation="Review this script for malicious intent.",
                                )
                            )
    return findings


def detect_scheduled_tasks(repo_path: str) -> List[dict]:
    """Detect scripts that may create scheduled tasks (cron, at, Task Scheduler, launchd)."""
    findings: List[dict] = []
    patterns = [
        (r'(^|\s)(crontab\s+-e|\(.*\)\s*>>\s*/var/spool/cron|@reboot\s+)', "cron modification", "Persistence via cron"),
        (r'(^|\s)(systemctl\s+enable\s+|/etc/systemd/system/)', "systemd service", "Persistence via systemd"),
        (r'\bschtasks\s+/create\b', "schtasks create", "Windows scheduled task"),
        (r'(^|\s)(launchctl\s+load\s+|/Library/LaunchAgents|/Library/LaunchDaemons)', "launchd agent", "macOS persistence"),
        (r'\bat\s+', "at command", "Scheduled via at"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".js", ".ts", ".py", ".rb", ".pl", ".yaml", ".yml", ".json", ".txt", ".cfg", ".conf", ".ini"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Potential scheduled task creation: {description}",
                                category="Persistence",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Command or pattern that could establish persistence via {description.lower()}.",
                                recommendation="Review this code for legitimacy; persistence mechanisms are often malicious.",
                            )
                        )
    return findings


def detect_registry_persistence(repo_path: str) -> List[dict]:
    """Detect attempts to modify Windows registry for persistence."""
    findings: List[dict] = []
    patterns = [
        (r'\breg\s+add\b', "reg add", "Add registry key"),
        (r'\breg\s+write\b', "reg write", "Write registry value"),
        (r'\bWScript\.Shell\b', "WScript.Shell", "Windows Script Host shell object"),
        (r'\bSet-ItemProperty\s+-Path\s+HKCU:', "Set-ItemProperty HKCU", "PowerShell registry write"),
        (r'\bSet-ItemProperty\s+-Path\s+HKLM:', "Set-ItemProperty HKLM", "PowerShell registry write"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Potential registry modification: {description}",
                                category="Persistence",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests modification of Windows registry for persistence.",
                                recommendation="Review this code; registry modifications can establish persistence.",
                            )
                        )
    return findings


def detect_startup_folder(repo_path: str) -> List[dict]:
    """Detect references to startup folders."""
    findings: List[dict] = []
    patterns = [
        (r'\\\\AppData\\\\Roaming\\\\Microsoft\\\\Windows\\\\Start Menu\\\\Programs\\\\Startup', "Windows Startup folder", "Reference to Windows Startup folder"),
        (r'%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup', "Windows Startup folder via env var", "Reference to Windows Startup folder"),
        (r'/Library/LaunchAgents', "macOS LaunchAgents", "Reference to macOS LaunchAgents"),
        (r'/Library/LaunchDaemons', "macOS LaunchDaemons", "Reference to macOS LaunchDaemons"),
        (r'~/Library/LaunchAgents', "User LaunchAgents", "Reference to user LaunchAgents"),
        (r'/etc/rc\.d', "init.d script", "Reference to init.d directory"),
        (r'/etc/init\.d', "init.d script", "Reference to init.d directory"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py", ".rb", ".sh", ".bash"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Potential startup folder reference: {description}",
                                category="Persistence",
                                severity=Severity.MEDIUM,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Reference to {description} that could be used for persistence.",
                                recommendation="Verify legitimacy; autostart mechanisms can be abused.",
                            )
                        )
    return findings


def detect_credential_theft_patterns(repo_path: str) -> List[dict]:
    """Detect patterns indicative of credential theft."""
    findings: List[dict] = []
    patterns = [
        (r'\bsecretsdump\b', "secretsdump", "LSASS memory dump tool"),
        (r'\bmimikatz\b', "mimikatz", "Credential dumping tool"),
        (r'\bprocdump\b.*-ma', "procdump dump", "Memory dumping"),
        (r'\bcsrss\.exe\b', "csrss.exe", "Possible process injection target"),
        (r'/etc/(shadow|passwd|group)', "/etc/passwd shadow", "Attempt to read sensitive system files"),
        (r'\bsudo\s+-k\b', "sudo -k", "Potential sudo token manipulation"),
        (r'Cookies\s*\\', "browser cookies", "Reference to browser cookies"),
        (r'Local\s*State', "Chrome Local State", "Chrome local state file"),
        (r'Keychains?', "Keychain", "macOS Keychain reference"),
        (r'\bsecurity\s+find-generic-password\b', "security find-generic-password", "macOS keychain access"),
        (r'\.ssh/', ".ssh directory", "Reference to SSH directory"),
        (r'id_rsa|id_dsa|id_ecdsa|id_ed25519', "SSH key file", "Reference to SSH private key"),
        (r'\bgetenv\s*\(', "getenv", "Environment variable retrieval"),
        (r'\b_?\w*[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\w*_?\b', "password-like variable", "Variable name suggests password"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py", ".rb", ".sh", ".bash", ".pl", ".java", ".cpp", ".c", ".cs", ".go", ".rs"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Potential credential theft indicator: {description}",
                                category="Credential Theft",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests attempt to steal credentials: {description}.",
                                recommendation="Review this code; credential theft is highly malicious.",
                            )
                        )
    return findings


def detect_ssh_key_access(repo_path: str) -> List[dict]:
    """Detect attempts to read SSH private or public keys."""
    findings: List[dict] = []
    patterns = [
        (r'\.ssh\/id_[rsa|dsa|ecdsa|ed25519]', "SSH private key file", "Reference to SSH private key"),
        (r'\.ssh\/id_rsa\.pub', "SSH public key", "Reference to SSH public key"),
        (r'\bcat\s+~/\.ssh/', "cat SSH dir", "Attempt to read SSH directory"),
        (r'\bcp\s+~/\.ssh/', "copy SSH dir", "Attempt to copy SSH keys"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py", ".rb", ".sh", ".bash", ".pl"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"SSH key access pattern: {description}",
                                category="Credential Theft",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests access to SSH keys: {description}.",
                                recommendation="SSH key theft can lead to remote server compromise.",
                            )
                        )
    return findings


def detect_browser_cookie_theft(repo_path: str) -> List[dict]:
    """Detect attempts to steal browser cookies."""
    findings: List[dict] = []
    patterns = [
        (r'AppData\\Local\\Google\\Chrome\\User Data\\.*\\Cookies', "Chrome cookies", "Reference to Chrome cookies file"),
        (r'AppData\\Local\\Microsoft\\Edge\\User Data\\.*\\Cookies', "Edge cookies", "Reference to Edge cookies file"),
        (r'Application Support\/Google\/Chrome\/.*\/Cookies', "Chrome cookies macOS", "Reference to Chrome cookies on macOS"),
        (r'Library\/Application Support\/Firefox\/Profiles\/.*\/cookies\.sqlite', "Firefox cookies", "Reference to Firefox cookies sqlite"),
        (r'\bcookie\b.*\b(steal| harvest| exfiltrate)\b', "cookie theft keyword", "Keyword combination suggesting cookie theft"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py", ".rb", ".sh", ".bash"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Potential browser cookie theft: {description}",
                                category="Credential Theft",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests attempt to access browser cookies: {description}.",
                                recommendation="Stealing cookies can lead to session hijacking.",
                            )
                        )
    return findings


def detect_env_harvesting(repo_path: str) -> List[dict]:
    """Detect collection of environment variables."""
    findings: List[dict] = []
    patterns = [
        (r'\benviron\b', "environ", "Access to environment variables (C/Python)"),
        (r'\bgetenv\s*\(', "getenv", "Get environment variable (C/PHP)"),
        (r'\bprocess\.env\b', "process.env", "Node.js environment variables"),
        (r'\b\_\_env\_\_\b', "__env__", "Python os.environ"),
        (r'\$\(env:\)', "env:", "PowerShell environment variable syntax"),
        (r'\bset\b', "set", "Windows batch variable display (could be used to dump)"),
        (r'\bprintenv\b', "printenv", "Unix command to print environment"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py", ".rb", ".sh", ".bash", ".pl", ".java", ".cpp", ".c", ".cs", ".go", ".rs"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Environment variable access: {description}",
                                category="Information Leak",
                                severity=Severity.MEDIUM,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Code accesses environment variables, which may contain secrets.",
                                recommendation="Ensure no sensitive data is leaked via logs or network.",
                            )
                        )
    return findings


def detect_dotenv_harvesting(repo_path: str) -> List[dict]:
    """Detect attempts to read .env files."""
    findings: List[dict] = []
    patterns = [
        (r'\.env\b', ".env file", "Reference to dotenv file"),
        (r'\bdotenv\b', "dotenv", "Dotenv library usage"),
        (r'\bload\.env\b', "load.env", "Function to load dotenv"),
        (r'\bparse\.env\b', "parse.env", "Parsing dotenv"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs", ".sh", ".bash"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Dotenv file access: {description}",
                                category="Information Leak",
                                severity=Severity.MEDIUM,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Code appears to read .env file, which may contain secrets.",
                                recommendation="Ensure .env is not committed and access is legitimate.",
                            )
                        )
    return findings


def detect_cloud_credential_access(repo_path: str) -> List[dict]:
    """Detect attempts to access cloud provider credentials."""
    findings: List[dict] = []
    patterns = [
        (r'\.aws\/credentials', "AWS credentials file", "Reference to AWS credentials"),
        (r'\bAWS_ACCESS_KEY_ID\b', "AWS access key env", "AWS access key environment variable"),
        (r'\bAWS_SECRET_ACCESS_KEY\b', "AWS secret key env", "AWS secret key environment variable"),
        (r'\bAWS_SESSION_TOKEN\b', "AWS session token env", "AWS session token environment variable"),
        (r'\bfrom\s+boto3\b', "boto3 import", "AWS SDK for Python"),
        (r'\bfrom\s+botocore\b', "botocore import", "AWS low-level SDK"),
        (r'\bapplication_default_credentials\.json\b', "GCP ADC", "Google Cloud Application Default Credentials"),
        (r'\bGOOGLE_APPLICATION_CREDENTIALS\b', "GCP ADC env var", "Environment variable for GCP credits"),
        (r'\bfrom\s+google\.cloud\b', "google.cloud import", "Google Cloud client library"),
        (r'\bAZURE_CLIENT_ID\b', "Azure client ID env", "Azure AD client ID"),
        (r'\bAZURE_TENANT_ID\b', "Azure tenant ID env", "Azure AD tenant ID"),
        (r'\bAZURE_CLIENT_SECRET\b', "Azure client secret env", "Azure AD client secret"),
        (r'\bfrom\s+azure\b', "azure import", "Azure SDK"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs", ".sh", ".bash", ".json", ".env", ".ini", ".cfg", ".txt"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Cloud credential access: {description}",
                                category="Cloud Credentials",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests access to {description.lower()}.",
                                recommendation="Cloud credential exposure can lead to compromise of cloud resources.",
                            )
                        )
    return findings


def detect_crypto_wallet_access(repo_path: str) -> List[dict]:
    """Detect attempts to access cryptocurrency wallet files."""
    findings: List[dict] = []
    patterns = [
        (r'\bwallet\.dat\b', "wallet.dat", "Bitcoin Core wallet file"),
        (r'\.bitcoin\/', ".bitcoin directory", "Bitcoin data directory"),
        (r'\.ethereum\/', ".ethereum directory", "Ethereum data directory"),
        (r'keystore\/', "keystore directory", "Ethereum keystore"),
        (r'\bjsonrpc\b.*localhost:8545', "JSON-RPC localhost", "Potential local Ethereum node RPC"),
        (r'\bwallet\b', "wallet", "Generic wallet reference"),
        (r'\bprivate.*key\b', "private key", "Reference to private key"),
        (r'\bseed\s+phrase\b', "seed phrase", "Reference to mnemonic seed phrase"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".py", ".js", ".ts", ".java", ".go", ".rb", ".sh", ".bash", ".pl", ".json", ".txt", ".csv", ".dat"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Potential cryptocurrency wallet access: {description}",
                                category="Cryptocurrency",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests access to cryptocurrency wallet: {description}.",
                                recommendation="Wallet theft can lead to irreversible loss of funds.",
                            )
                        )
    return findings


def detect_network_exfiltration(repo_path: str) -> List[dict]:
    """Detect patterns that may exfiltrate data over the network."""
    findings: List[dict] = []
    patterns = [
        (r'\bwget\s+http[s]?://', "wget HTTP", "Download via HTTP"),
        (r'\bcurl\s+http[s]?://', "curl HTTP", "Download via HTTP"),
        (r'\bInvoke-WebRequest\s+http[s]?://', "Invoke-WebRequest HTTP", "PowerShell download"),
        (r'\bInvoke-RestMethod\s+http[s]?://', "Invoke-RestMethod HTTP", "PowerShell REST"),
        (r'\bbitsadmin\b', "bitsadmin", "Background Intelligent Transfer Service"),
        (r'\bftp\s+', "ftp", "FTP command"),
        (r'\btftp\b', "tftp", "TFTP command"),
        (r'\bcurl\s+-T\s+', "curl upload", "cURL upload file"),
        (r'\bwget\s+--post-file\s+', "wget post file", "wget upload"),
        (r'\bsftp\b', "sftp", "SFTP command"),
        (r'\bscp\b', "scp", "Secure copy"),
        (r'pastebin\.com', "pastebin.com", "Pastebin URL"),
        (r'hastebin\.com', "hastebin.com", "Hastebin URL"),
        (r'\bcontrolc\.com\b', "controlc.com", "ControlC URL"),
        (r'\bdiscordapp\.com\/api\/webhooks\b', "discord webhook", "Discord webhook URL"),
        (r'\bapi\.telegram\.org\b', "telegram bot api", "Telegram bot API"),
        (r'\bdocs\.google\.com\/*forms\/*', "google forms", "Google Forms endpoint"),
        (r'\bdrive\.google\.com\/*uc\?export=download\b', "google drive download", "Google Drive direct download"),
        (r'\bdropbox\.com\/*', "dropbox.com", "Dropbox link"),
        (r'\btrycloudflare\.com\b', "trycloudflare.com", "Cloudflare tunnel"),
        (r'\bngrok\b', "ngrok", "ngrok tunnel"),
        (r'\b\.onion\b', ".onion domain", "Tor hidden service"),
        (r'\bdyndns\b', "dyndns", "Dynamic DNS provider"),
        (r'\bno-ip\.com\b', "no-ip.com", "Dynamic DNS provider"),
    ]
    from app.core.constants import IGNORED_DIRS

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in {".bat", ".cmd", ".ps1", ".vbs", ".js", ".ts", ".py", ".rb", ".sh", ".bash", ".pl", ".json", ".txt", ".csv", ".log", ".ini", ".cfg", ".conf"}:
                continue
            full_path = os.path.join(root, file)
            if _is_binary_file(full_path):
                continue
            lines = _read_lines(full_path)
            if not lines:
                continue
            for i, line in enumerate(lines, start=1):
                for pattern, _, description in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(
                            _make_finding(
                                title=f"Network exfiltration indicator: {description}",
                                category="Network Exfiltration",
                                severity=Severity.HIGH,
                                file_path=os.path.relpath(full_path, repo_path),
                                line=i,
                                description=f"Pattern suggests potential data exfiltration: {description}.",
                                recommendation="Review this network activity for legitimacy.",
                            )
                        )
    return findings