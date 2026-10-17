"""Would a clinic's own child/adult model, learned from attested sessions, label new children better?

The app can train a small model on the sessions a therapist has attested
(``src/audio_pipeline/clinic_speaker_model.py``). This script simulates that
on TalkBank recordings whose CHAT transcripts time and label every utterance:

1. Each recording's gold utterance spans go through the USC frame model; each
   utterance becomes one feature row (the app's own ``utterance_features``),
   labelled child or adult from the transcript.
2. **Same clinic**: each recording is a new child; the model is trained on
   N other recordings of the same corpus (same examiners, same task) and
   tested on that child, against the frame model alone. N = 1, 2, 4, 8 and
   all others; random picks are repeated.
3. **Another clinic**: trained on every other corpus, tested on this one.
4. The app's own adoption check (``train_clinic_head``: each child held out
   in turn) on each corpus, to see whether the app would switch.

Features are cached under ``--cache-dir`` so a rerun only trains.

Usage:
    python scripts/evaluate_clinic_speaker_model.py \\
        --corpus enni=.local/evaluation/enni_media \\
        --corpus ellisweismer=.local/evaluation/ellisweismer_media \\
        --corpus crslp=.local/evaluation/crslp_media

Each corpus folder holds the media and a ``chat/`` folder of transcripts.
Outputs: reports/metrics/clinic_speaker_model.{md,csv}
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_speaker_attribution import CHILD, collect_recordings  # noqa: E402
from src.audio_pipeline.clinic_speaker_model import (  # noqa: E402
    LabelledSession,
    fit_head,
    frame_margins,
    train_clinic_head,
    utterance_features,
)

CURVE_SIZES = (1, 2, 4, 8)
REPEATS = 5
OLDER_MONTHS = 84  # the frame model's labels are flagged from this age


@dataclass
class Child:
    corpus: str
    child_id: str  # a folder per child (CRSLP) or a recording per child
    recording: str
    age_months: float | None
    design: np.ndarray
    is_child: np.ndarray


def load_corpus(name: str, folder: Path, cache_dir: Path, minutes: float) -> list[Child]:
    cha_dir = folder / "chat"
    recordings, skipped = collect_recordings(cha_dir, folder, max_minutes=minutes, limit=None)
    for reason in skipped:
        print(f"  skipped {reason}")
    model = None
    children = []
    for rec in recordings:
        relative = rec.cha_path.parent.relative_to(cha_dir).parts
        cached = cache_dir / name / f"{'_'.join(relative)}_{rec.cha_path.stem}.npz"
        spans = [(u.start, u.end) for u in rec.utterances]
        is_child = np.array([u.role == CHILD for u in rec.utterances], dtype=int)
        try:
            design = np.load(cached)["design"]
            assert len(design) == len(spans)
        except (OSError, KeyError, AssertionError):
            from faster_whisper.audio import decode_audio

            from src.audio_pipeline.child_adult_frames import SAMPLE_RATE, ChildAdultFrameModel

            model = model or ChildAdultFrameModel()
            audio = decode_audio(str(rec.audio_path), sampling_rate=SAMPLE_RATE)[: int(minutes * 60 * SAMPLE_RATE)]
            design = utterance_features(*model.frame_outputs(audio), spans)
            cached.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cached, design=design)
            print(f"  {name} {rec.cha_path.stem}: {len(spans)} utterances")
        # CRSLP keeps one folder per child with several sessions; elsewhere each recording is a child.
        child_id = relative[0] if name == "crslp" and relative else rec.cha_path.stem
        children.append(Child(name, f"{name}:{child_id}", rec.cha_path.stem, rec.age_months, design, is_child))
    return children


def accuracy(head, child: Child) -> float:
    return float(((head.margins(child.design) > 0) == child.is_child).mean())


def frame_accuracy(child: Child) -> float:
    return float(((frame_margins(child.design) > 0) == child.is_child).mean())


def same_clinic_curve(children: list[Child], rng) -> list[dict]:
    rows = []
    ids = sorted({c.child_id for c in children})
    for size in CURVE_SIZES + (None,):
        for held in ids:
            test = [c for c in children if c.child_id == held]
            others = [c for c in children if c.child_id != held]
            picks = [others] if size is None else [
                list(rng.choice(others, size=min(size, len(others)), replace=False)) for _ in range(REPEATS)
            ]
            for train in picks:
                y = np.concatenate([c.is_child for c in train])
                if y.min() == y.max():
                    continue
                head = fit_head(np.vstack([c.design for c in train]), y)
                for child in test:
                    rows.append({"setting": "same clinic", "corpus": child.corpus, "train_sessions": size or len(others),
                                 "size_label": "all others" if size is None else str(size), "recording": child.recording,
                                 "age_months": child.age_months, "utterances": len(child.is_child),
                                 "model_accuracy": accuracy(head, child), "frame_accuracy": frame_accuracy(child)})
    return rows


def other_clinic(corpora: dict[str, list[Child]]) -> list[dict]:
    rows = []
    for name, test in corpora.items():
        train = [c for other, children in corpora.items() if other != name for c in children]
        if not train:
            continue
        head = fit_head(np.vstack([c.design for c in train]), np.concatenate([c.is_child for c in train]))
        for child in test:
            rows.append({"setting": "other clinic", "corpus": name, "train_sessions": len(train), "size_label": "other corpora",
                         "recording": child.recording, "age_months": child.age_months, "utterances": len(child.is_child),
                         "model_accuracy": accuracy(head, child), "frame_accuracy": frame_accuracy(child)})
    return rows


def pooled(rows: list[dict], key: str) -> float:
    """Utterance-weighted accuracy over recordings (and repeats)."""
    total = sum(r["utterances"] for r in rows)
    return sum(r[key] * r["utterances"] for r in rows) / total if total else float("nan")


def write_report(rows: list[dict], adoption: dict, corpora: dict[str, list[Child]], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "clinic_speaker_model.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def bucket(corpus: str, older: bool | None):
        def keep(r):
            if r["corpus"] != corpus:
                return False
            return older is None or r["age_months"] is None or (r["age_months"] >= OLDER_MONTHS) == older
        return keep

    groups = []
    for corpus in corpora:
        ages = [c.age_months for c in corpora[corpus] if c.age_months]
        if corpus == "enni":
            groups += [("ENNI under 7", bucket(corpus, False)), ("ENNI 7 and over", bucket(corpus, True))]
        else:
            label = {"ellisweismer": "EllisWeismer", "crslp": "CRSLP (Thai)"}.get(corpus, corpus)
            groups.append((f"{label} ({min(ages):.0f}-{max(ages):.0f} months)" if ages else label, bucket(corpus, None)))

    sizes = [str(s) for s in CURVE_SIZES] + ["all others"]
    lines = [
        "# A Clinic's Own Child/Adult Model",
        "",
        "Simulates the app learning from a therapist's attested sessions: a logistic regression on the",
        "USC frame model's encoder features (`src/audio_pipeline/clinic_speaker_model.py`), trained on",
        "some recordings and tested on a child it has not heard. Speaker spans and labels come from the",
        "corpus transcripts, so only speaker attribution is measured. Utterance-weighted accuracy;",
        f"random picks repeated {REPEATS} times. Run with `scripts/evaluate_clinic_speaker_model.py`.",
        "",
        "## Same clinic: trained on N other sessions of the same corpus",
        "",
        "| Children | Frame model | " + " | ".join(f"N = {s}" for s in sizes) + " |",
        "|---|---|" + "---|" * len(sizes),
    ]
    for title, keep in groups:
        same = [r for r in rows if r["setting"] == "same clinic" and keep(r)]
        if not same:
            continue
        frame = pooled([r for r in same if r["size_label"] == "all others"], "frame_accuracy")
        cells = [f"{pooled([r for r in same if r['size_label'] == s], 'model_accuracy'):.0%}" for s in sizes]
        lines.append(f"| {title} | {frame:.0%} | " + " | ".join(cells) + " |")
    lines += ["", "## Another clinic: trained on the other corpora only", "", "| Children | Frame model | Clinic model |", "|---|---|---|"]
    for title, keep in groups:
        other = [r for r in rows if r["setting"] == "other clinic" and keep(r)]
        if other:
            lines.append(f"| {title} | {pooled(other, 'frame_accuracy'):.0%} | {pooled(other, 'model_accuracy'):.0%} |")
    lines += ["", "## Would the app switch? (its own check: each child held out in turn, all sessions)", "",
              "The app compares balanced accuracy, the mean of the share of child and of adult utterances",
              "labelled right, so a model cannot win by calling everyone adult.", "",
              "| Corpus | Sessions | Children | Accuracy, frame / clinic | Balanced accuracy, frame / clinic | Adopted |",
              "|---|---|---|---|---|---|"]
    for corpus, result in adoption.items():
        lines.append(f"| {corpus} | {result.sessions} | {result.children} | {result.frame_accuracy:.1%} / {result.model_accuracy:.1%} | "
                     f"{result.frame_balanced:.1%} / {result.model_balanced:.1%} | {'yes' if result.adopted else 'no'} |")
    lines += ["", "## Reading these numbers", "",
              "- Within one corpus the recordings share a task, a setting and possibly examiners, as a",
              "  clinic's sessions share its therapists. That is what the clinic model learns: it helps most",
              "  where the frame model fails, ENNI children of 7 and over whose voices are heard as adults.",
              "- Trained on other corpora it does not carry over, so the app learns per clinic and never",
              "  ships a trained model.",
              "- Where the frame model is already good (EllisWeismer, 2;6-5;6) the clinic model ties with it",
              "  and the app keeps the frame model.",
              "- Thai toddlers: plain accuracy rises only by calling more utterances adult; balanced accuracy",
              "  falls, and the app keeps the frame model.",
              "- English and Thai-toddler recordings only; not yet tried in a Thai clinic. Labels outside",
              "  30-83 months stay flagged for the therapist whichever model made them."]
    (report_dir / "clinic_speaker_model.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", action="append", required=True, metavar="NAME=FOLDER")
    parser.add_argument("--max-minutes", type=float, default=10.0)
    parser.add_argument("--cache-dir", type=Path, default=PROJECT_ROOT / ".local" / "evaluation" / "speaker_features")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "metrics")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    corpora = {}
    for spec in args.corpus:
        name, _, folder = spec.partition("=")
        corpora[name] = load_corpus(name, Path(folder).expanduser(), args.cache_dir, args.max_minutes)
    rng = np.random.default_rng(args.seed)
    rows = [r for children in corpora.values() for r in same_clinic_curve(children, rng)] + other_clinic(corpora)
    adoption = {
        name: train_clinic_head(LabelledSession(c.recording, c.child_id, c.design, c.is_child) for c in children)
        for name, children in corpora.items()
    }
    write_report(rows, adoption, corpora, args.report_dir)
    print(f"Wrote {args.report_dir / 'clinic_speaker_model.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
