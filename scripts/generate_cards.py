from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
DEFAULT_INPUT = ROOT / "data" / "input_videos.csv"
DEFAULT_OUT = ROOT / "output"


@dataclass
class ImportRow:
    row_number: int
    source_url: str
    platform: str
    published_at: date
    author: str
    title_or_caption: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    duration_sec: int
    topic_hint: str
    notes: str


@dataclass
class ValidationIssue:
    row_number: int
    field: str
    message: str


@dataclass
class ScoredCard:
    selected: bool
    selection_reason: str
    rejection_reasons: list[str]
    source_url: str
    platform: str
    published_at: str
    author: str
    title_or_caption: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    duration_sec: int
    topic_hint: str
    notes: str
    raw_score: int
    engagement_score: float
    recency_score: float
    neuropravo_fit_score: float
    final_score: float
    why_it_worked: str
    mechanic: str
    new_topic: str
    hook: str
    structure: str
    script: str
    video_description: str
    video_title: str
    cta: str


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def parse_number(value: str, field: str, row_number: int, issues: list[ValidationIssue]) -> int:
    raw = (value or "").strip().replace(" ", "").replace("_", "").replace(",", ".")
    if raw == "":
        return 0
    multiplier = 1
    suffix = raw[-1:].lower()
    if suffix in {"k", "к"}:
        multiplier = 1_000
        raw = raw[:-1]
    elif suffix in {"m", "м"}:
        multiplier = 1_000_000
        raw = raw[:-1]
    try:
        number = float(raw) * multiplier
    except ValueError:
        issues.append(ValidationIssue(row_number, field, f"число не парсится: {value!r}"))
        return 0
    if number < 0:
        issues.append(ValidationIssue(row_number, field, "число не может быть отрицательным"))
        return 0
    return int(round(number))


def parse_date(value: str, row_number: int, issues: list[ValidationIssue]) -> date | None:
    raw = (value or "").strip()
    if not raw:
        issues.append(ValidationIssue(row_number, "published_at", "дата обязательна"))
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    issues.append(ValidationIssue(row_number, "published_at", "используй дату YYYY-MM-DD"))
    return None


def days_old(published_at: date) -> int:
    return (date.today() - published_at).days


def normalize_text(*values: str) -> str:
    return " ".join(value or "" for value in values).lower().replace("ё", "е")


def validate_header(headers: Iterable[str], required_fields: list[str]) -> list[ValidationIssue]:
    present = set(headers or [])
    return [
        ValidationIssue(1, field, "обязательное поле отсутствует в заголовке")
        for field in required_fields
        if field not in present
    ]


def load_rows(input_path: Path, config: dict) -> tuple[list[ImportRow], list[ValidationIssue]]:
    rows: list[ImportRow] = []
    issues: list[ValidationIssue] = []
    allowed_platforms = set(config["allowed_platforms"])
    required_fields = config["required_fields"]
    window_days = int(config["window_days"])

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        issues.extend(validate_header(reader.fieldnames or [], required_fields))
        if issues:
            return [], issues

        for index, row in enumerate(reader, start=2):
            for field in required_fields:
                if row.get(field) is None:
                    issues.append(ValidationIssue(index, field, "обязательное поле отсутствует"))

            source_url = (row.get("source_url") or "").strip()
            if not source_url:
                issues.append(ValidationIssue(index, "source_url", "URL не должен быть пустым"))

            platform = (row.get("platform") or "").strip()
            if platform not in allowed_platforms:
                issues.append(ValidationIssue(index, "platform", f"platform должен быть одним из: {', '.join(sorted(allowed_platforms))}"))

            published_at = parse_date(row.get("published_at", ""), index, issues)
            if published_at is not None:
                age = days_old(published_at)
                if age < 0:
                    issues.append(ValidationIssue(index, "published_at", "дата публикации не может быть в будущем"))
                elif age > window_days:
                    issues.append(ValidationIssue(index, "published_at", f"дата старше {window_days} дней"))

            views = parse_number(row.get("views", ""), "views", index, issues)
            likes = parse_number(row.get("likes", ""), "likes", index, issues)
            comments = parse_number(row.get("comments", ""), "comments", index, issues)
            shares = parse_number(row.get("shares", ""), "shares", index, issues)
            saves = parse_number(row.get("saves", ""), "saves", index, issues)
            duration_sec = parse_number(row.get("duration_sec", ""), "duration_sec", index, issues)

            if published_at is None:
                continue

            rows.append(
                ImportRow(
                    row_number=index,
                    source_url=source_url,
                    platform=platform,
                    published_at=published_at,
                    author=(row.get("author") or "").strip(),
                    title_or_caption=(row.get("title_or_caption") or "").strip(),
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    saves=saves,
                    duration_sec=duration_sec,
                    topic_hint=(row.get("topic_hint") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                )
            )

    return rows, issues


def raw_score(row: ImportRow) -> int:
    return row.views + row.comments * 30 + row.likes * 3 + row.shares * 30 + row.saves * 40


def engagement_score(row: ImportRow) -> float:
    if row.views <= 0:
        return 0.0
    engagement_units = row.likes + row.comments * 6 + row.shares * 8 + row.saves * 10
    ratio = engagement_units / row.views
    return round(min(100.0, ratio * 600), 2)


def recency_score(row: ImportRow, window_days: int) -> float:
    age = max(0, days_old(row.published_at))
    return round(max(0.0, 100.0 * (1 - age / max(window_days, 1))), 2)


def neuropravo_fit_score(row: ImportRow, config: dict) -> float:
    text = normalize_text(row.title_or_caption, row.topic_hint, row.notes)
    topics = [topic.lower().replace("ё", "е") for topic in config["topics"]]
    signals = [signal.lower().replace("ё", "е") for signal in config["fit_signals"]]
    topic_hits = sum(1 for topic in topics if topic and topic in text)
    signal_hits = sum(1 for signal in signals if signal and signal in text)
    score = min(100.0, topic_hits * 24 + signal_hits * 8)
    if row.topic_hint.strip():
        score = min(100.0, score + 12)
    return round(score, 2)


def normalized_raw_score(score: int) -> float:
    if score <= 0:
        return 0.0
    return round(min(100.0, math.log10(score + 1) / 6 * 100), 2)


def final_score(raw: int, engagement: float, recency: float, fit: float) -> float:
    normalized_raw = normalized_raw_score(raw)
    return round(normalized_raw * 0.35 + engagement * 0.20 + recency * 0.20 + fit * 0.25, 2)


def build_reasons(row: ImportRow, final: float, fit: float, config: dict, min_score: float) -> tuple[bool, str, list[str]]:
    rules = config["selection_rules"]
    rejection: list[str] = []
    if days_old(row.published_at) > int(config["window_days"]):
        rejection.append("дата старше 30 дней")
    if row.duration_sec > int(rules["max_duration_sec"]):
        rejection.append("длительность больше лимита короткого формата")
    if fit < float(rules["min_neuropravo_fit_score"]):
        rejection.append("слабая привязка к темам НейроПраво")
    if final < min_score:
        rejection.append(f"final_score ниже порога {min_score:g}")
    selected = not rejection
    if selected:
        return True, "отобран: свежий ролик, достаточный score и понятная legal/biz-боль", []
    return False, "отсеян: " + "; ".join(rejection), rejection


def first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return "Обычная ситуация внезапно стала спором из-за денег, сроков и доказательств."
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return parts[0][:180]


def compact_script(row: ImportRow) -> str:
    hook = first_sentence(row.title_or_caption)
    topic = row.topic_hint or "спорная ситуация"
    return (
        f"Представьте: все начинается не с суда и не с громкой юридической истории. {hook} Сначала это выглядит как обычная бытовая или рабочая ситуация: договорились, поверили, перевели деньги, подождали еще пару дней. И именно в этот момент часто закладывается будущая проблема."
        "\n\n"
        f"В теме `{topic}` опасность обычно не в том, что человек сразу делает что-то явно неправильное. Опасность в том, что он оставляет слишком много на словах. Нет точной суммы, нет срока, нет подтверждения, нет нормального следа в переписке. Пока отношения спокойные, это кажется лишней формальностью."
        "\n\n"
        "А потом появляется конфликт. Один говорит: 'мы так не договаривались'. Второй показывает переписку, но там только эмоции и обрывки фраз. Третий вспоминает устный разговор, который уже невозможно подтвердить. И спор начинает крутиться не вокруг справедливости, а вокруг доказательств."
        "\n\n"
        "Вот почему сильная позиция часто создается заранее, а не в момент ссоры. Короткое сообщение с суммой и сроком, чек, файл, акт, подтверждение условий в чате - это не бюрократия ради бюрократии. Это способ не зависеть только от чужой памяти и доброй воли."
        "\n\n"
        "Неожиданный вывод такой: доверие не отменяет фиксацию. Наоборот, нормальная фиксация часто сохраняет отношения, потому что всем понятно, кто что обещал, когда и за какие деньги. Чем меньше тумана в начале, тем меньше пространства для конфликта потом."
        "\n\n"
        "Если у вас похожая ситуация, не делайте вывод по одному ролику и не ищите универсальную волшебную фразу. В каждом деле важны документы, даты, суммы, переписка и детали. Но общий принцип простой: если договоренность важна для денег, имущества или срока, у нее должен быть понятный след."
    )


def build_card(row: ImportRow, config: dict, min_score: float) -> ScoredCard:
    raw = raw_score(row)
    engagement = engagement_score(row)
    recency = recency_score(row, int(config["window_days"]))
    fit = neuropravo_fit_score(row, config)
    final = final_score(raw, engagement, recency, fit)
    selected, reason, rejection = build_reasons(row, final, fit, config, min_score)
    topic = row.topic_hint or "спорная ситуация"
    hook = first_sentence(row.title_or_caption)
    return ScoredCard(
        selected=selected,
        selection_reason=reason,
        rejection_reasons=rejection,
        source_url=row.source_url,
        platform=row.platform,
        published_at=row.published_at.isoformat(),
        author=row.author,
        title_or_caption=row.title_or_caption,
        views=row.views,
        likes=row.likes,
        comments=row.comments,
        shares=row.shares,
        saves=row.saves,
        duration_sec=row.duration_sec,
        topic_hint=row.topic_hint,
        notes=row.notes,
        raw_score=raw,
        engagement_score=engagement,
        recency_score=recency,
        neuropravo_fit_score=fit,
        final_score=final,
        why_it_worked=(
            "Есть узнаваемый конфликт, измеримые последствия и точка напряжения: деньги, срок, доверие, "
            "переписка или документы. Такой ролик можно адаптировать как механику, не копируя текст."
        ),
        mechanic=(
            "Короткий hook через потерю или риск, бытовая деталь, затем разворот: проблема не в эмоциях, "
            "а в том, что доказательства и условия появились слишком поздно."
        ),
        new_topic=f"{topic}: как заранее оставить след договоренности и не спорить только на эмоциях.",
        hook=hook,
        structure=(
            "1. Сцена и hook. 2. Почему человек решил 'и так нормально'. 3. Где возник риск. "
            "4. Ошибка с деньгами, сроком или перепиской. 5. Неожиданный вывод. 6. Мягкий CTA."
        ),
        script=compact_script(row),
        video_description="Разбор бытовой или предпринимательской ошибки: почему договоренности лучше фиксировать до конфликта, а не после.",
        video_title=f"{topic}: ошибка, которая всплывает слишком поздно",
        cta="Смотрите на документы, даты, суммы и переписку. В споре часто решает не ощущение правоты, а следы договоренности.",
    )


def write_markdown(cards: list[ScoredCard], issues: list[ValidationIssue], output_path: Path, input_path: Path, min_score: float) -> None:
    selected = [card for card in cards if card.selected]
    rejected = [card for card in cards if not card.selected]
    lines = [
        "# Карточки сценариев НейроПраво",
        "",
        f"Входной CSV: `{input_path}`",
        f"Порог final_score: `{min_score:g}`",
        f"Сгенерировано локально: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Важно: это черновики для ручного выбора. Не публикация, не юридическая консультация, не рендер.",
        "",
        f"Отобрано: {len(selected)} из {len(cards)}",
        "",
    ]
    if issues:
        lines.extend(["## Ошибки валидации", ""])
        for issue in issues:
            lines.append(f"- строка {issue.row_number}, `{issue.field}`: {issue.message}")
        lines.append("")
    if rejected:
        lines.extend(["## Отсеянные кандидаты", ""])
        for card in rejected:
            lines.append(f"- {card.platform} | {card.source_url} | final_score={card.final_score}: {card.selection_reason}")
        lines.append("")
    for card in selected:
        lines.extend(
            [
                "---",
                "",
                f"# {card.video_title}",
                "",
                f"Источник: [{card.source_url}]({card.source_url})",
                f"Платформа: {card.platform}",
                f"Автор: {card.author}",
                f"Дата: {card.published_at}",
                f"Длительность: {card.duration_sec} сек.",
                "",
                f"raw_score: {card.raw_score}",
                f"engagement_score: {card.engagement_score}",
                f"recency_score: {card.recency_score}",
                f"neuropravo_fit_score: {card.neuropravo_fit_score}",
                f"final_score: {card.final_score}",
                f"Решение: {card.selection_reason}",
                "",
                "## Почему мог залететь",
                "",
                card.why_it_worked,
                "",
                "## Механика",
                "",
                card.mechanic,
                "",
                "## Новая тема для НейроПраво",
                "",
                card.new_topic,
                "",
                "## Hook",
                "",
                card.hook,
                "",
                "## Структура",
                "",
                card.structure,
                "",
                "## Сценарий",
                "",
                card.script,
                "",
                "## Описание",
                "",
                card.video_description,
                "",
                "## CTA",
                "",
                card.cta,
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(cards: list[ScoredCard], output_path: Path) -> None:
    fields = list(asdict(cards[0]).keys()) if cards else ["selected", "selection_reason"]
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for card in cards:
            row = asdict(card)
            row["rejection_reasons"] = "; ".join(card.rejection_reasons)
            writer.writerow(row)


def write_json(cards: list[ScoredCard], issues: list[ValidationIssue], output_path: Path) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cards": [asdict(card) for card in cards],
        "validation_issues": [asdict(issue) for issue in issues],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_validation_report(issues: list[ValidationIssue], output_path: Path) -> None:
    lines = ["row_number,field,message"]
    for issue in issues:
        lines.append(f'{issue.row_number},{issue.field},"{issue.message.replace(chr(34), chr(34) + chr(34))}"')
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate NeuroPravo short-video scenario cards from import CSV.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to import CSV.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory.")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum final_score for selected cards.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    min_score = float(args.min_score if args.min_score is not None else config.get("default_min_score", 70))

    rows, issues = load_rows(input_path, config)
    cards = [build_card(row, config, min_score) for row in rows]
    cards.sort(key=lambda card: card.final_score, reverse=True)

    write_markdown(cards, issues, out_dir / "scenario_cards.md", input_path, min_score)
    write_json(cards, issues, out_dir / "scenario_cards.json")
    if cards:
        write_csv(cards, out_dir / "scenario_cards.csv")
    else:
        (out_dir / "scenario_cards.csv").write_text("selected,selection_reason\n", encoding="utf-8-sig")
    write_validation_report(issues, out_dir / "validation_report.csv")

    selected_count = sum(1 for card in cards if card.selected)
    print(f"Done: {out_dir}")
    print(f"Valid rows: {len(rows)}")
    print(f"Selected videos: {selected_count} of {len(cards)}")
    print(f"Validation issues: {len(issues)}")
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())
