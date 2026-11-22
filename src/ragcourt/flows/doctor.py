"""Doctor: a model describes your documents, recommends chunkers and may write one; all are measured (§12).

The generated chunker is shown in full with its SHA-256 and runs only after the user's yes, or with
``--approve`` naming exactly that hash (D-017); it runs in a separate process with a timeout (not a
sandbox); its output must be text of each document; then it is ranked with the baselines on the same
held-out questions and called better only when the paired interval says so.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ragcourt import stages
from ragcourt.core.doctor import (
    chunker_menu,
    code_hash,
    read_advice,
    read_code,
    sample,
    samples_text,
    validate,
)
from ragcourt.core.leaderboard import Scoring, board, by_category, ranked_categories, values
from ragcourt.core.relevance import token_map
from ragcourt.core.stats import paired_difference, resamples, separable
from ragcourt.core.verdicts import fill
from ragcourt.errors import GeneratedCodeRejected
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.questions import QuestionOptions, ensure_questions
from ragcourt.flows.run_plan import RankOptions, settings_of
from ragcourt.io import run_files
from ragcourt.io.ask import confirm
from ragcourt.io.isolated_run import run_chunker
from ragcourt.io.narration import roles_text
from ragcourt.io.project import Project
from ragcourt.io.prompts import load_prompt
from ragcourt.io.rank_output import board_text
from ragcourt.io.result_data import board_data
from ragcourt.io.terminal import printable
from ragcourt.stages.specs import parse_spec
from ragcourt.types import Corpus
from ragcourt.types.results import Board, Evaluation, PipelineSpec

Say = Callable[[str], None]
NOT_A_SANDBOX = (
    "It runs in a separate process with a timeout. That is not a sandbox: your approval is the safety step."
)


@dataclass(frozen=True)
class DoctorOptions:
    """What the command line asked for."""

    questions: QuestionOptions
    approve: str | None = None
    write_code: bool = True
    timeout: float = 10.0
    embedder: str | None = None


def run_doctor(project: Project, corpus: Corpus, options: DoctorOptions, say: Say) -> int:
    """Describe, recommend, maybe write; ask; run isolated; validate; measure."""
    doctor = project.role("doctor")
    say(roles_text([doctor]))
    samples = samples_text(sample(corpus.documents, project.config.seed))
    model = doctor.models[0]
    describe = load_prompt("doctor.describe", project.config.prompts_dir).text
    advice = read_advice(project.chat(model)(fill(describe, chunkers=chunker_menu(), samples=samples)))
    say(_advice_text(advice.structure, advice.recommended, advice.dropped))
    baselines = {str(parse_spec(spec)) for spec in project.config.search.chunkers}
    candidates = [spec for spec, _ in advice.recommended if str(parse_spec(spec)) not in baselines]
    for spec, _ in advice.recommended:
        if str(parse_spec(spec)) in baselines:
            say(f"{spec} is already a baseline: it is measured as one.")
    generated = _generated(project, corpus, options, samples, say) if options.write_code else None
    if generated:
        candidates.append(generated)
    if not candidates:
        say("Nothing to measure.")
        return 0
    return _measure(project, corpus, options, candidates, say)


def _advice_text(
    structure: dict[str, str], recommended: list[tuple[str, str]], dropped: list[tuple[str, str]]
) -> str:
    lines = ["", "What the documents look like:"]
    lines += [f"  {key}: {value}" for key, value in structure.items()]
    lines += ["Recommended chunkers:"] + [f"  {spec}: {why}" for spec, why in recommended]
    lines += [f"  dropped {spec!r}: {why}" for spec, why in dropped]
    return "\n".join(lines)


def _generated(
    project: Project, corpus: Corpus, options: DoctorOptions, samples: str, say: Say
) -> str | None:
    """The generated chunker's stage name once approved, run and validated on every document; else None."""
    write = load_prompt("doctor.write", project.config.prompts_dir).text
    code = read_code(
        project.chat(project.role("doctor").models[0], json_reply=False)(fill(write, samples=samples))
    )
    if code is None:
        say("The model wrote no usable chunker (no `def chunk(text)`).")
        return None
    if printable(code) != code:
        say("Rejected: the code holds control or bidirectional characters, which could hide part of it.")
        return None
    digest = code_hash(code)
    path = project.workdir / "doctor" / f"{digest[:16]}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")
    say(f"\nThe chunker the model wrote ({path}):\n\n{code}\nSHA-256: {digest}\n{NOT_A_SANDBOX}")
    if not _approved(options.approve, digest):
        mismatch = options.approve is not None
        say("Not run: --approve does not match this code's SHA-256." if mismatch else "Not run.")
        return None
    try:
        return _register(path, digest, corpus, options.timeout)
    except GeneratedCodeRejected as error:
        say(f"Rejected: {error}")
        return None


def _approved(approve: str | None, digest: str) -> bool:
    if approve is not None:
        return approve == digest
    return confirm("Run this code on your documents?", yes=False)


def _register(path: Path, digest: str, corpus: Corpus, timeout: float) -> str:
    """Run the code on every document, validate the output, and register it as a chunker stage."""
    outputs: dict[str, list[str]] = {}
    for document in corpus.documents:
        if code_hash(path.read_text(encoding="utf-8")) != digest:
            raise GeneratedCodeRejected(f"{path} changed after it was approved; nothing more was run.")
        outputs[document.text] = validate(document, run_chunker(path, document.text, timeout))
    name = f"doctor-{digest[:8]}"

    def generated(text: str) -> list[str]:
        return outputs[text]

    stages.register("chunker", name, generated)
    return name


def _measure(
    project: Project,
    corpus: Corpus,
    options: DoctorOptions,
    extra: list[str],
    say: Say,
) -> int:
    questions = ensure_questions(project, corpus, options.questions, say)
    held = [question for question in questions if question.split == "held-out"]
    embedder = options.embedder or project.role("embedders").models[0]
    baselines = list(project.config.search.chunkers)
    folder = run_files.new_run(
        project.workdir, {"doctor": extra, "baselines": baselines, "embedder": embedder}
    )
    settings = settings_of(project, RankOptions(options.questions))
    texts = {document.id: document.text for document in corpus.documents}
    evaluator = Evaluator(project, corpus, questions, settings, token_map(texts), folder)
    evaluations = [
        evaluator.evaluate(PipelineSpec(spec, embedder, "dense", "none")) for spec in [*baselines, *extra]
    ]
    draws = {
        name: resamples(len(members), project.config.search.resamples, f"{project.config.seed}:{name}")
        for name, members in by_category(held).items()
    }
    scoring = Scoring(held, project.config.search.metric, project.config.questions.min_held_out, draws)
    leaderboard = board("chunker", evaluations, scoring)
    say(board_text(board_data(leaderboard), None))
    for name in extra:
        say(_verdict(name, evaluations, (leaderboard, baselines), scoring))
    return 0


def _verdict(
    name: str, evaluations: list[Evaluation], ranked: tuple[Board, list[str]], scoring: Scoring
) -> str:
    """Better, worse or no significant difference, against the leaderboard's best baseline (held-out)."""
    candidate = next(item for item in evaluations if item.spec.chunker == name)
    best = _best_baseline(evaluations, *ranked)
    difference = paired_difference(
        _by_category(candidate, scoring), _by_category(best, scoring), scoring.draws
    )
    if not separable(difference):
        word = "no significant difference from"
    elif difference.mean > 0:
        word = "better than"
    else:
        word = "worse than"
    span = f"{difference.mean:+.2f} [{difference.low:+.2f}, {difference.high:+.2f}]"
    return f"{name}: {word} the best baseline, {best.spec.chunker} ({span})."


def _best_baseline(evaluations: list[Evaluation], leaderboard: Board, baselines: list[str]) -> Evaluation:
    """The highest baseline on the leaderboard."""
    by_spec = {
        evaluation.spec: evaluation for evaluation in evaluations if evaluation.spec.chunker in baselines
    }
    best = next(row.spec for row in leaderboard.rows if row.spec in by_spec)
    return by_spec[best]


def _by_category(evaluation: Evaluation, scoring: Scoring) -> dict[str, list[float]]:
    """The categories the leaderboard ranks (not those too few to rank), so verdict and board agree."""
    ranked, _ = ranked_categories(scoring.questions, scoring.min_per_category)
    groups = by_category(scoring.questions)
    return {name: values(evaluation, groups[name], scoring.metric) for name in ranked}
