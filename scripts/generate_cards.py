from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
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
    editorial_decision: str
    why_not_copying: str
    what_to_change_for_neuropravo: str
    legal_safe_boundary: str
    metrics_mode: str
    metrics_completeness: str
    recency_quality: str


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


def metrics_incomplete(row: ImportRow) -> bool:
    notes = normalize_text(row.notes)
    explicit_markers = (
        "unknown",
        "approximate",
        "visible_on_page",
        "not visible",
        'не видно',
        'неизвест',
        'примерн',
    )
    has_marker = any(marker in notes for marker in explicit_markers)
    missing_reactions = row.views > 0 and row.likes <= 0 and row.comments <= 0 and row.shares <= 0 and row.saves <= 0
    return has_marker or missing_reactions


def recency_is_approximate(row: ImportRow) -> bool:
    notes = normalize_text(row.notes)
    return "approximate" in notes or "collection date" in notes or 'дата сбора' in notes or 'примерн' in notes


def detect_metrics_mode(rows: list[ImportRow], requested_mode: str) -> str:
    if requested_mode in {"normal", "public_search"}:
        return requested_mode
    if not rows:
        return "normal"
    incomplete_count = sum(1 for row in rows if metrics_incomplete(row))
    with_views_count = sum(1 for row in rows if row.views > 0)
    if with_views_count and incomplete_count / len(rows) >= 0.50:
        return "public_search"
    return "normal"


def metrics_completeness_label(row: ImportRow, metrics_mode: str) -> str:
    parts: list[str] = []
    if metrics_incomplete(row):
        parts.append("incomplete_public_metrics")
    if row.likes <= 0 and row.comments <= 0:
        parts.append("likes_comments_unknown_or_zero")
    if recency_is_approximate(row):
        parts.append("published_at_approximate")
    if metrics_mode == "public_search":
        parts.append("public_search_weighting")
    return "; ".join(dict.fromkeys(parts)) or "complete_enough"


def engagement_score(row: ImportRow, metrics_mode: str = "normal") -> float:
    if row.views <= 0:
        return 0.0
    engagement_units = row.likes + row.comments * 6 + row.shares * 8 + row.saves * 10
    if metrics_mode == "public_search" and metrics_incomplete(row):
        # Public search often shows views but hides reactions. Keep engagement neutral, not punitive.
        return round(min(55.0, 30.0 + normalized_raw_score(row.views) * 0.20), 2)
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


def final_score(raw: int, engagement: float, recency: float, fit: float, metrics_mode: str = "normal") -> float:
    normalized_raw = normalized_raw_score(raw)
    if metrics_mode == "public_search":
        return round(normalized_raw * 0.45 + engagement * 0.05 + recency * 0.15 + fit * 0.35, 2)
    return round(normalized_raw * 0.35 + engagement * 0.20 + recency * 0.20 + fit * 0.25, 2)


def build_reasons(row: ImportRow, final: float, fit: float, config: dict, min_score: float, metrics_mode: str = "normal") -> tuple[bool, str, list[str]]:
    rules = config["selection_rules"]
    rejection: list[str] = []
    if days_old(row.published_at) > int(config["window_days"]):
        rejection.append('дата старше 30 дней')
    if row.duration_sec > int(rules["max_duration_sec"]):
        rejection.append('длительность больше лимита короткого формата')
    if fit < float(rules["min_neuropravo_fit_score"]):
        rejection.append('слабая привязка к темам НейроПраво')
    if final < min_score:
        rejection.append(f"final_score ниже порога {min_score:g}")
    if metrics_mode == "public_search" and metrics_incomplete(row):
        has_visible_public_signal = row.views >= 5000 or (fit >= 68 and row.views >= 800)
        if not has_visible_public_signal:
            rejection.append('public_search: мало видимых просмотров для неполных метрик')
    selected = not rejection
    if selected:
        if metrics_mode == "public_search" and metrics_incomplete(row):
            return True, 'отобран: public_search, метрики неполные; score рассчитан без жесткого штрафа за unknown likes/comments', []
        return True, 'отобран: свежий ролик, достаточный score и понятная legal/biz-боль', []
    if metrics_mode == "public_search" and metrics_incomplete(row):
        rejection.append('метрики неполные public_search, shortlist требует ручной проверки')
    return False, 'отсеян: ' + "; ".join(rejection), rejection


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


def editorial_decision(selected: bool, final: float, fit: float, rejection: list[str]) -> str:
    if selected and final >= 82 and fit >= 55:
        return "брать"
    if selected or (final >= 65 and fit >= 40 and not any("дата старше" in reason for reason in rejection)):
        return "подумать"
    return "отложить"


def build_card(row: ImportRow, config: dict, min_score: float, metrics_mode: str = "normal") -> ScoredCard:
    raw = raw_score(row)
    engagement = engagement_score(row, metrics_mode)
    recency = recency_score(row, int(config["window_days"]))
    fit = neuropravo_fit_score(row, config)
    final = final_score(raw, engagement, recency, fit, metrics_mode)
    selected, reason, rejection = build_reasons(row, final, fit, config, min_score, metrics_mode)
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
        editorial_decision=editorial_decision(selected, final, fit, rejection),
        why_not_copying="Берем только механику: конфликт, темп, боль и поворот. Текст, примеры, формулировки и вывод пересобираются заново под НейроПраво.",
        what_to_change_for_neuropravo=f"Сместить фокус с чужой истории на практический риск в теме `{topic}`: деньги, сроки, документы, переписка и доказательства.",
        legal_safe_boundary="Не обещать результат, не разбирать персональное дело зрителя и не давать универсальную инструкцию. Говорить как о типовой ситуации: важны документы, даты, суммы и детали.",
        metrics_mode=metrics_mode,
        metrics_completeness=metrics_completeness_label(row, metrics_mode),
        recency_quality="approximate" if recency_is_approximate(row) else "exact_or_imported",
    )


def topic_label(card: ScoredCard) -> str:
    return (card.topic_hint or "без темы").strip().lower()


def quality_counters(cards: list[ScoredCard], issues: list[ValidationIssue], config: dict) -> dict:
    rows_without_views = sum(1 for card in cards if card.views <= 0)
    rows_without_reactions = sum(1 for card in cards if card.likes <= 0 and card.comments <= 0)
    rejection_counter = Counter(reason for card in cards for reason in card.rejection_reasons)
    incomplete_metrics = sum(1 for card in cards if "incomplete_public_metrics" in card.metrics_completeness)
    approximate_dates = sum(1 for card in cards if card.recency_quality == "approximate")
    return {
        "total_videos": len(cards),
        "platforms": Counter(card.platform for card in cards),
        "topics": Counter(topic_label(card) for card in cards),
        "older_than_window": sum(1 for card in cards if days_old(datetime.strptime(card.published_at, "%Y-%m-%d").date()) > int(config["window_days"])),
        "without_views": rows_without_views,
        "without_likes_or_comments": rows_without_reactions,
        "incomplete_metrics": incomplete_metrics,
        "approximate_dates": approximate_dates,
        "rejection_reasons": rejection_counter,
    }


def write_batch_summary(cards: list[ScoredCard], issues: list[ValidationIssue], output_path: Path, input_path: Path, min_score: float, config: dict, metrics_mode: str) -> None:
    selected = [card for card in cards if card.selected]
    rejected = [card for card in cards if not card.selected]
    counters = quality_counters(cards, issues, config)
    top_final = sorted(cards, key=lambda card: card.final_score, reverse=True)[:10]
    top_fit = sorted(cards, key=lambda card: card.neuropravo_fit_score, reverse=True)[:5]
    first_watch = [card for card in top_final if card.editorial_decision in {"брать", "подумать"}][:10]

    lines = [
        "# Batch Summary",
        "",
        f"Входной CSV: `{input_path}`",
        f"Порог final_score: `{min_score:g}`",
        f"Сгенерировано локально: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Это редакторская сводка для быстрого выбора идей. Ничего не публикует и не рендерит.",
        "",
        "## Качество партии",
        "",
        f"- Всего роликов: {counters['total_videos']}",
        f"- Отобрано: {len(selected)}",
        f"- Отсеяно: {len(rejected)}",
        f"- Ошибок валидации: {len(issues)}",
        f"- Роликов старше {config['window_days']} дней: {counters['older_than_window']}",
        f"- Без просмотров: {counters['without_views']}",
        f"- Без лайков и комментариев: {counters['without_likes_or_comments']}",
        "",
        "## Data quality / Metrics completeness",
        "",
        f"- Metrics mode: `{metrics_mode}`",
        f"- Rows with incomplete public metrics: {counters['incomplete_metrics']}",
        f"- Rows with approximate published_at: {counters['approximate_dates']}",
        "- In `public_search`, unknown likes/comments are not treated as negative engagement when notes say metrics are not visible.",
        "- This shortlist is editorial: manually open candidates before production.",
        "",
        "## Платформы",
        "",
    ]
    for platform, count in counters["platforms"].most_common():
        lines.append(f"- {platform}: {count}")
    lines.extend(["", "## Темы", ""])
    for topic, count in counters["topics"].most_common():
        lines.append(f"- {topic}: {count}")
    lines.extend(["", "## Причины отсева", ""])
    if counters["rejection_reasons"]:
        for reason, count in counters["rejection_reasons"].most_common():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- Нет отсева по правилам.")
    lines.extend(["", "## Смотреть первыми", ""])
    if first_watch:
        for index, card in enumerate(first_watch, start=1):
            lines.append(f"{index}. {card.editorial_decision.upper()} | final={card.final_score} | fit={card.neuropravo_fit_score} | {card.platform} | {card.video_title}")
            lines.append(f"   {card.source_url}")
    else:
        lines.append("Нет кандидатов уровня 'брать' или 'подумать'. Лучше собрать новую партию.")
    lines.extend(["", "## Топ-10 по final_score", ""])
    for index, card in enumerate(top_final, start=1):
        lines.append(f"{index}. final={card.final_score} | fit={card.neuropravo_fit_score} | {card.editorial_decision} | {card.platform} | {card.source_url}")
    lines.extend(["", "## Топ-5 по neuropravo_fit_score", ""])
    for index, card in enumerate(top_fit, start=1):
        lines.append(f"{index}. fit={card.neuropravo_fit_score} | final={card.final_score} | {card.editorial_decision} | {card.topic_hint} | {card.source_url}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def viral_status(card: ScoredCard) -> str:
    if card.selected and card.final_score >= 70 and card.neuropravo_fit_score >= 40:
        return "ЗАЛЕТЕВШИЙ-КАНДИДАТ"
    if card.editorial_decision in {"брать", "подумать"} and card.final_score >= 55:
        return "ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ"
    return "НЕ БРАТЬ"


def adaptation_distance(card: ScoredCard) -> str:
    if card.editorial_decision == "брать":
        return "сильная переработка: берем механику конфликта, но меняем героя, ситуацию, формулировки, вывод и CTA"
    if card.editorial_decision == "подумать":
        return "только после ручного просмотра: возможно взять hook или конфликт, текст не копировать"
    return "не адаптировать без отдельного решения"


def write_source_review(cards: list[ScoredCard], issues: list[ValidationIssue], output_path: Path, input_path: Path, min_score: float, metrics_mode: str) -> None:
    lines = [
        "# Source Candidates Review",
        "",
        f"Входной CSV: `{input_path}`",
        f"Metrics mode: `{metrics_mode}`",
        f"Порог final_score: `{min_score:g}`",
        f"Сгенерировано локально: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Цель файла: сначала показать исходный материал и доказательства сигнала, и только потом разрешать сценарии.",
        "Сценарий не считается рабочим результатом, если у кандидата нет исходной ссылки, метрик, причины залета и проверки на НейроПраво.",
        "",
        "## Правило допуска к сценарию",
        "",
        "- `ЗАЛЕТЕВШИЙ-КАНДИДАТ`: можно отдавать Окну 2 на сценарий после ручного просмотра исходника.",
        "- `ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ`: смотреть вручную; сценарий только если Александр/контролер подтвердил смысл.",
        "- `НЕ БРАТЬ`: не писать сценарий.",
        "",
        "## Кандидаты",
        "",
        "| # | status | decision | final | fit | views | reactions | date | platform | topic | source | why selected / rejected | adaptation distance |",
        "|---:|---|---|---:|---:|---:|---:|---|---|---|---|---|---|",
    ]
    for index, card in enumerate(cards, start=1):
        reactions = card.likes + card.comments + card.shares + card.saves
        topic = (card.topic_hint or "без темы").replace("|", "/")
        reason = card.selection_reason.replace("|", "/")
        distance = adaptation_distance(card).replace("|", "/")
        lines.append(
            f"| {index} | {viral_status(card)} | {card.editorial_decision} | {card.final_score} | {card.neuropravo_fit_score} | {card.views} | {reactions} | {card.published_at} | {card.platform} | {topic} | {card.source_url} | {reason} | {distance} |"
        )
    if issues:
        lines.extend(["", "## Validation issues", ""])
        for issue in issues:
            lines.append(f"- строка {issue.row_number}, `{issue.field}`: {issue.message}")
    lines.extend([
        "",
        "## Контролерское правило",
        "",
        "Окно 2 не получает задание на сценарий, пока кандидат не имеет статуса `ЗАЛЕТЕВШИЙ-КАНДИДАТ` или вручную подтвержденного `ПОТЕНЦИАЛЬНЫЙ-СИГНАЛ`.",
        "Копирование текста, персонажа, последовательности фраз и чужого вывода запрещено. Разрешено переносить только механику: боль, конфликт, темп, поворот и тип зрительского интереса.",
    ])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
def write_markdown(cards: list[ScoredCard], issues: list[ValidationIssue], output_path: Path, input_path: Path, min_score: float, metrics_mode: str) -> None:
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
                f"Редакторское решение: {card.editorial_decision}",
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
                "## Почему это не копирование",
                "",
                card.why_not_copying,
                "",
                "## Что изменить под НейроПраво",
                "",
                card.what_to_change_for_neuropravo,
                "",
                "## Юридически безопасная граница",
                "",
                card.legal_safe_boundary,
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
    parser.add_argument(
        "--metrics-mode",
        choices=["auto", "normal", "public_search"],
        default="auto",
        help="Scoring mode: normal for complete imports, public_search for open search batches with incomplete reactions/dates.",
    )
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
    metrics_mode = detect_metrics_mode(rows, args.metrics_mode)
    cards = [build_card(row, config, min_score, metrics_mode) for row in rows]
    cards.sort(key=lambda card: card.final_score, reverse=True)

    write_markdown(cards, issues, out_dir / "scenario_cards.md", input_path, min_score, metrics_mode)
    write_batch_summary(cards, issues, out_dir / "batch_summary.md", input_path, min_score, config, metrics_mode)
    write_source_review(cards, issues, out_dir / "source_candidates_review.md", input_path, min_score, metrics_mode)
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
    print(f"Metrics mode: {metrics_mode}")
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())

