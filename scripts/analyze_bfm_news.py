from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "business_fm_news" / "business_fm_news_2026-07-13.csv"
DEFAULT_OUT = ROOT / "output" / "business_fm_news_2026-07-13"
RULES_PATH = ROOT / "config" / "business_fm_signal_rules.json"


@dataclass
class NewsItem:
    source_url: str
    source_name: str
    published_at: str
    title: str
    text: str
    notes: str


@dataclass
class NewsScore:
    item: NewsItem
    relevance: int
    viral_potential: int
    avatar_fit: int
    neuropravo_fit: int
    total: int
    decision: str
    reasons: list[str]
    hook: str
    compact_script: str


def normalize(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def load_rules() -> dict:
    with RULES_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_items(input_path: Path) -> list[NewsItem]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            NewsItem(
                source_url=(row.get("source_url") or "").strip(),
                source_name=(row.get("source_name") or "").strip(),
                published_at=(row.get("published_at") or "").strip(),
                title=(row.get("title") or "").strip(),
                text=(row.get("text") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
            for row in reader
        ]


def count_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if normalize(keyword) in text)


def score_bucket(text: str, keywords: list[str], max_score: int) -> int:
    hits = count_hits(text, keywords)
    return min(max_score, hits * 2)


def detect_reasons(text: str, rules: dict) -> list[str]:
    reasons: list[str] = []
    signals = rules["positive_signals"]
    if count_hits(text, signals["human_business_pain"]):
        reasons.append("есть человеческая или деловая боль")
    if count_hits(text, signals["money_or_control_risk"]):
        reasons.append("есть риск денег, доступа, связи, репутации или контроля")
    if count_hits(text, signals["viral_emotion"]):
        reasons.append("есть эмоциональный крючок для Reels")
    if count_hits(text, signals["neuropravo_fit"]):
        reasons.append("есть практический правовой угол для НейроПраво")
    return reasons


def make_hook(item: NewsItem) -> str:
    text = normalize(f"{item.title} {item.text}")
    if "спам" in text and "номер" in text:
        return "Вы звоните клиенту, а телефон уже решил за него: вам лучше не отвечать."
    if "банк" in text or "карта" in text or "счет" in text:
        return "Вы ничего не нарушали, но доступ к деньгам внезапно стал вопросом поддержки."
    if "маркетплейс" in text or "платформа" in text:
        return "Ваш бизнес может остановить не клиент и не конкурент, а решение платформы."
    if "оператор" in text or "связь" in text:
        return "Иногда сделку срывает не человек, а связь, которая решила, что вы проблема."
    title = item.title.rstrip(".!?")
    return title if title else "Вы все делали нормально, но система решила иначе."


def compact_script(item: NewsItem, hook: str) -> str:
    text = normalize(f"{item.title} {item.text}")
    if "спам" in text and "номер" in text:
        return "\n".join(
            [
                hook,
                "",
                "Не реклама. Не обзвон. Обычный рабочий звонок.",
                "Но на той стороне появляется предупреждение: возможно, спам.",
                "",
                "Вы еще ничего не сказали, а доверие уже сломано.",
                "",
                "Для человека это неприятно.",
                "Для бизнеса это может стоить клиента, записи, поставки или сделки.",
                "",
                "Самое опасное здесь то, что вы можете не знать причину.",
                "Кто-то пожаловался. Алгоритм ошибся. Система увидела много звонков и решила, что вы подозрительны.",
                "",
                "Что делать?",
                "Попросите скрин предупреждения.",
                "Запишите дату и время звонка.",
                "Уточните, какое приложение или сервис поставили метку.",
                "Потом обращайтесь к оператору и в поддержку сервиса спокойно, с фактами.",
                "",
                "Репутация теперь есть даже у номера телефона.",
                "И если этот номер кормит бизнес, за ним нужно следить так же, как за отзывами и документами.",
            ]
        )
    return "\n".join(
        [
            hook,
            "",
            "На первый взгляд это техническая мелочь.",
            "Но для бизнеса такие мелочи быстро превращаются в деньги, сроки и потерянное доверие.",
            "",
            "Проблема начинается не тогда, когда уже спор.",
            "Она начинается в момент, когда человек не понимает, кто принял решение и как его оспорить.",
            "",
            "В такой ситуации важны не эмоции, а следы.",
            "Что произошло, когда, где это видно, кто ответил и что можно приложить к обращению.",
            "",
            "Система может ошибаться.",
            "Но защищаться от ошибки системы нужно не криком, а понятной цепочкой фактов.",
        ]
    )


def score_item(item: NewsItem, rules: dict) -> NewsScore:
    text = normalize(f"{item.title} {item.text} {item.notes}")
    signals = rules["positive_signals"]
    relevance = score_bucket(text, signals["human_business_pain"], 10)
    viral = score_bucket(text, signals["viral_emotion"], 10)
    neuro = score_bucket(text, signals["neuropravo_fit"], 10)
    avatar = 8 if relevance >= 2 and viral >= 2 else 4
    if any(negative in text for negative in map(normalize, rules["negative_signals"])):
        relevance = max(0, relevance - 4)
        viral = max(0, viral - 3)
    total = relevance + viral + avatar + neuro
    script_now = int(rules["score_thresholds"]["script_now"])
    watchlist = int(rules["score_thresholds"]["watchlist"])
    if total >= script_now:
        decision = "SCRIPT-NOW"
    elif total >= watchlist:
        decision = "WATCHLIST"
    else:
        decision = "SKIP"
    hook = make_hook(item)
    return NewsScore(
        item=item,
        relevance=relevance,
        viral_potential=viral,
        avatar_fit=avatar,
        neuropravo_fit=neuro,
        total=total,
        decision=decision,
        reasons=detect_reasons(text, rules),
        hook=hook,
        compact_script=compact_script(item, hook) if decision == "SCRIPT-NOW" else "",
    )


def write_review(scores: list[NewsScore], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sorted_scores = sorted(scores, key=lambda score: score.total, reverse=True)
    lines = [
        "# Business FM news review",
        "",
        f"Дата анализа: {date.today().isoformat()}",
        "",
        "Правило: Business FM news -> релевантность -> вирусность -> avatar-office fit -> сценарий.",
        "",
        "## Итог",
        "",
    ]
    counts = {decision: sum(1 for score in scores if score.decision == decision) for decision in ("SCRIPT-NOW", "WATCHLIST", "SKIP")}
    for decision, count in counts.items():
        lines.append(f"- {decision}: {count}")
    lines.extend(["", "## Кандидаты", ""])
    for index, score in enumerate(sorted_scores, start=1):
        item = score.item
        lines.extend(
            [
                f"### {index}. {item.title}",
                "",
                f"- decision: {score.decision}",
                f"- total: {score.total}",
                f"- relevance: {score.relevance}",
                f"- viral_potential: {score.viral_potential}",
                f"- neuropravo_fit: {score.neuropravo_fit}",
                f"- avatar_fit: {score.avatar_fit}",
                f"- source: {item.source_name}",
                f"- url: {item.source_url or 'manual/telegram'}",
                f"- hook: {score.hook}",
                f"- reasons: {', '.join(score.reasons) if score.reasons else 'нет сильных сигналов'}",
                "",
            ]
        )
        if score.compact_script:
            lines.extend(["#### Compact script", "", score.compact_script, ""])
    (out_dir / "business_fm_news_review.md").write_text("\n".join(lines), encoding="utf-8")


def write_csv(scores: list[NewsScore], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "business_fm_news_review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "decision",
                "total",
                "relevance",
                "viral_potential",
                "neuropravo_fit",
                "avatar_fit",
                "title",
                "hook",
                "source_url",
            ],
        )
        writer.writeheader()
        for score in sorted(scores, key=lambda item: item.total, reverse=True):
            writer.writerow(
                {
                    "decision": score.decision,
                    "total": score.total,
                    "relevance": score.relevance,
                    "viral_potential": score.viral_potential,
                    "neuropravo_fit": score.neuropravo_fit,
                    "avatar_fit": score.avatar_fit,
                    "title": score.item.title,
                    "hook": score.hook,
                    "source_url": score.item.source_url,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Business FM news as NeuroPravo Reels scenario sources.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="CSV with Business FM news items")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output folder")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    rules = load_rules()
    items = load_items(input_path)
    scores = [score_item(item, rules) for item in items]
    write_review(scores, out_dir)
    write_csv(scores, out_dir)
    print(f"Done: {out_dir}")
    print(f"Items: {len(scores)}")
    print(f"Script now: {sum(1 for score in scores if score.decision == 'SCRIPT-NOW')}")


if __name__ == "__main__":
    main()
