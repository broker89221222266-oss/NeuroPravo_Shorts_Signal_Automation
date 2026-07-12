from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
INPUT_PATH = ROOT / "data" / "input_videos.csv"
OUTPUT_PATH = ROOT / "output" / "scenario_cards.md"


@dataclass
class VideoCandidate:
    url: str
    platform: str
    published_at: date
    author: str
    author_average_views: int
    views: int
    likes: int
    comments: int
    shares: int | None
    saves: int | None
    description: str
    opening_seconds: str
    topic: str
    conflict: str


def parse_int(value: str) -> int:
    value = (value or "").strip()
    return int(value) if value else 0


def parse_optional_int(value: str) -> int | None:
    value = (value or "").strip()
    return int(value) if value else None


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_candidates() -> list[VideoCandidate]:
    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            VideoCandidate(
                url=row["url"],
                platform=row["platform"],
                published_at=datetime.strptime(row["published_at"], "%Y-%m-%d").date(),
                author=row["author"],
                author_average_views=parse_int(row["author_average_views"]),
                views=parse_int(row["views"]),
                likes=parse_int(row["likes"]),
                comments=parse_int(row["comments"]),
                shares=parse_optional_int(row["shares"]),
                saves=parse_optional_int(row["saves"]),
                description=row["description"],
                opening_seconds=row["opening_seconds"],
                topic=row["topic"],
                conflict=row["conflict"],
            )
            for row in reader
        ]


def strength(video: VideoCandidate) -> int:
    if video.shares is not None and video.saves is not None:
        return video.views + video.comments * 20 + video.shares * 30 + video.saves * 40
    return video.views + video.comments * 30 + video.likes * 3


def relative_boost(video: VideoCandidate) -> float:
    return round(strength(video) / max(video.author_average_views, 1), 2)


def topic_fit(video: VideoCandidate, topics: list[str]) -> int:
    text = f"{video.description} {video.opening_seconds} {video.topic} {video.conflict}".lower()
    return sum(1 for topic in topics if topic.lower() in text)


def conflict_score(video: VideoCandidate) -> int:
    text = f"{video.description} {video.opening_seconds} {video.conflict}".lower()
    signals = [
        "деньг",
        "долг",
        "пропал",
        "аванс",
        "спор",
        "вернул",
        "договор",
        "переписк",
        "устн",
        "обещал",
        "доказательств",
    ]
    return sum(1 for signal in signals if signal in text)


def is_recent(video: VideoCandidate, window_days: int) -> bool:
    return video.published_at >= date.today() - timedelta(days=window_days)


def keep(video: VideoCandidate, config: dict) -> bool:
    minimums = config["minimums"]
    return (
        is_recent(video, config["window_days"])
        and relative_boost(video) >= minimums["relative_boost"]
        and conflict_score(video) >= minimums["conflict_score"]
        and topic_fit(video, config["topics"]) >= minimums["neuropravo_fit_score"]
    )


def compact_script(video: VideoCandidate) -> str:
    return (
        f"Представьте ситуацию: все начинается не с суда и не с большой юридической истории, "
        f"а с обычного человеческого доверия. {video.opening_seconds} Сначала кажется, что это мелочь: "
        f"сообщение в мессенджере, устная договоренность, аванс, обещание, что деньги будут завтра. "
        f"А потом именно эта мелочь становится главным слабым местом."
        "\n\n"
        f"В истории про {video.topic} конфликт почти всегда развивается одинаково: пока отношения нормальные, "
        f"люди не хотят фиксировать детали. Неловко просить договор, неловко уточнять сроки, неловко писать "
        f"простую фразу: что именно, за какую сумму и к какой дате должно произойти. Но когда начинается спор, "
        f"в памяти у каждого своя версия, а в документах часто пусто."
        "\n\n"
        f"Самая опасная ошибка здесь не в том, что человек кому-то поверил. Доверие само по себе нормально. "
        f"Ошибка в том, что доверие не оставило следа. Если {video.conflict}, потом приходится доказывать не только "
        f"свою правоту, но и саму реальность договоренности."
        "\n\n"
        "И вот здесь появляется неожиданный вывод: сильная позиция часто строится не в момент конфликта, "
        "а за пять минут до него. Одно подтверждение в переписке, один понятный чек, один файл, одна формулировка "
        "про срок и сумму могут потом значить больше, чем длинные эмоциональные объяснения."
        "\n\n"
        "Это не значит, что нужно жить в постоянном недоверии. Наоборот, нормальные правила берегут отношения. "
        "Когда все зафиксировано спокойно и заранее, меньше поводов спорить, меньше места для манипуляций и меньше "
        "шансов, что через месяц вам скажут: 'мы вообще не так договаривались'."
        "\n\n"
        "Если у вас похожая ситуация, не делайте вывод только по одному ролику. В каждом деле важны документы, "
        "переписка, даты, суммы и детали. Но как общий принцип запомните: чем проще договоренность выглядит сегодня, "
        "тем важнее оставить по ней понятный след."
    )


def card(video: VideoCandidate) -> str:
    score = strength(video)
    boost = relative_boost(video)
    title = f"Не поверил бы, если бы не переписка: {video.topic}"
    source = f"[{video.url}]({video.url})"
    why = (
        f"Есть понятный бытовой конфликт, деньги/сроки и точка узнавания. Ролик набрал примерно "
        f"{boost}x от среднего уровня автора, поэтому его стоит разобрать как механику внимания."
    )
    mechanic = (
        "Сначала короткий крючок через потерю или угрозу потери, затем бытовая деталь, затем разворот: "
        "проблема не в эмоциях, а в том, что доказательства появились слишком поздно."
    )
    structure = (
        "1. Бытовая сцена и hook. 2. Почему человек решил 'и так нормально'. 3. Где возник юридический риск. "
        "4. Ошибка с деньгами, сроком или перепиской. 5. Неожиданный вывод. 6. Мягкий CTA."
    )
    return f"""# {title}

Источник: {source}
Платформа: {video.platform}
Автор: {video.author}
Дата: {video.published_at.isoformat()}

Сила ролика: {score}
Выстрел относительно канала: {boost}x

## Почему мог залететь

{why}

## Механика

{mechanic}

## Новая тема для НейроПраво

{video.topic}: что делать, когда {video.conflict}.

## Hook

{video.opening_seconds}

## Структура

{structure}

## Сценарий

{compact_script(video)}

## Описание

Обычная договоренность может стать проблемой, если не осталось понятного следа: переписки, суммы, срока и подтверждения.

## CTA

Разберите свою ситуацию по документам и деталям, а не по ощущениям. Так меньше шансов пропустить главное.
"""


def main() -> None:
    config = load_config()
    candidates = load_candidates()
    kept = [video for video in candidates if keep(video, config)]
    ranked = sorted(kept, key=lambda item: (relative_boost(item), strength(item)), reverse=True)

    header = (
        "# Карточки сценариев НейроПраво\n\n"
        f"Сгенерировано локально: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "Важно: это черновики для ручного выбора. Не публикация, не юридическая консультация, не рендер.\n\n"
    )
    body = "\n\n---\n\n".join(card(video) for video in ranked)
    OUTPUT_PATH.write_text(header + body + "\n", encoding="utf-8")
    print("Done: output/scenario_cards.md")
    print(f"Selected videos: {len(ranked)} of {len(candidates)}")


if __name__ == "__main__":
    main()
