from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TodoComment:
    commit_sha: str
    file_path: str
    text: str


@dataclass(slots=True)
class CommitRecord:
    sha: str
    message: str
    authored_date: str
    author_name: str
    author_email: str
    html_url: str | None = None
    files_touched: list[str] = field(default_factory=list)
    todo_fixme_additions: list[TodoComment] = field(default_factory=list)
    risk_keywords_found: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReviewComment:
    text: str
    context: str
    source_url: str | None = None


@dataclass(slots=True)
class PRRecord:
    number: int
    title: str
    state: str
    merged: bool
    url: str
    unresolved_review_comments: list[ReviewComment] = field(default_factory=list)


@dataclass(slots=True)
class IssueRecord:
    number: int
    title: str
    state: str
    url: str
    body: str = ""
    comments: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BranchRecord:
    name: str
    last_commit_sha: str
    last_commit_message: str
    last_commit_date: str
    merged: bool = False
    deleted: bool = False
    source_url: str | None = None


@dataclass(slots=True)
class UnfinishedItem:
    type: str
    title: str
    description: str
    evidence: str
    source_url: str | None = None
    confidence: float = 0.7
    evidence_kind: str = "direct"


@dataclass(slots=True)
class WarningSignal:
    text: str
    context: str
    source_url: str | None = None
    severity: str = "medium"
    confidence: float = 0.7
    evidence_kind: str = "direct"


@dataclass(slots=True)
class ContributionProfile:
    author_handle: str
    repo: str
    commits: list[CommitRecord] = field(default_factory=list)
    prs_authored: list[PRRecord] = field(default_factory=list)
    issues_opened: list[IssueRecord] = field(default_factory=list)
    review_comments: list[ReviewComment] = field(default_factory=list)
    todo_comments: list[TodoComment] = field(default_factory=list)
    abandoned_branches: list[BranchRecord] = field(default_factory=list)
    warning_signals: list[WarningSignal] = field(default_factory=list)
    unfinished_items: list[UnfinishedItem] = field(default_factory=list)
    exclusive_files: list[str] = field(default_factory=list)
    bus_factor_modules: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WillDocument:
    author_handle: str
    repo: str
    generated_at: str
    mode: str
    unfinished: list[UnfinishedItem] = field(default_factory=list)
    warnings: list[WarningSignal] = field(default_factory=list)
    exclusive_knowledge: list[str] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    biggest_concern: str = ""
    markdown: str = ""

