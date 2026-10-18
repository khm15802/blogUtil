from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication, QImage, QPainter, QPen


CARD_WIDTH = 1080
CARD_HEIGHT = 1350
MASCOT_DIR = Path(__file__).resolve().parent / "assets" / "instagram_mascots"


@dataclass(frozen=True)
class Card:
    eyebrow: str
    title: str
    body: str


def _plain(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"[ \t]+", " ", html.unescape(value)).strip()


def extract_info(content_html: str) -> dict[str, str]:
    rows = re.findall(
        r"<tr[^>]*>\s*<td[^>]*>\s*(.*?)\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>\s*</tr>",
        content_html,
        flags=re.I | re.S,
    )
    return {_plain(label): _plain(value) for label, value in rows}


def build_cards(post: dict) -> list[Card]:
    info = extract_info(str(post.get("content_html", "")))
    title = str(post.get("title", "")).strip()
    category = str(post.get("category", "")).strip() or "ACTIVE LOG"
    summary = str(post.get("summary", "")).strip()
    sources = post.get("sources", [])
    if not sources and post.get("sources_json"):
        import json

        sources = json.loads(post["sources_json"])
    source_text = "\n".join(
        source.get("title", source.get("url", "")) if isinstance(source, dict) else str(source)
        for source in sources
    ).strip() or "공식 행사 안내"
    return [
        Card(category, title, summary),
        Card("WHEN", "언제 열리나요?", f"기간\n{info.get('기간', '공식 일정 확인')}\n\n운영 시간\n{info.get('운영 시간', '공식 안내 확인')}"),
        Card("WHERE", "어디에서 만나요?", f"장소\n{info.get('장소', '공식 장소 안내 확인')}"),
        Card("TICKET", "입장 전에 확인하세요", f"관람료\n{info.get('관람료', '공식 안내 확인')}"),
        Card("HIGHLIGHT", "무엇을 즐길 수 있나요?", info.get("주요 프로그램", summary)),
        Card("SAVE & SHARE", "일정은 저장해두세요", f"최신 내용은 공식 페이지에서 다시 확인하세요.\n\n출처 · {source_text}\n\nACTIVELOG"),
    ]


def _font(size: int, *, bold: bool = False) -> QFont:
    font = QFont("Malgun Gothic")
    font.setPixelSize(size)
    font.setBold(bold)
    return font


def _draw_wrapped(painter: QPainter, rect: QRectF, text: str, font: QFont, color: QColor) -> None:
    painter.setFont(font)
    painter.setPen(color)
    painter.drawText(rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, text)


def _draw_cover(painter: QPainter, card: Card, poster: QImage | None) -> None:
    if poster and not poster.isNull():
        scaled = poster.scaled(CARD_WIDTH, CARD_HEIGHT, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (scaled.width() - CARD_WIDTH) // 2)
        y = max(0, (scaled.height() - CARD_HEIGHT) // 2)
        painter.drawImage(QRectF(0, 0, CARD_WIDTH, CARD_HEIGHT), scaled, QRectF(x, y, CARD_WIDTH, CARD_HEIGHT))
        painter.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT, QColor(18, 36, 26, 150))
    else:
        painter.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT, QColor("#315b43"))
    painter.fillRect(70, 78, 330, 64, QColor("#f4b860"))
    _draw_wrapped(painter, QRectF(94, 91, 290, 45), card.eyebrow, _font(28, bold=True), QColor("#20372a"))
    _draw_wrapped(painter, QRectF(74, 720, 930, 390), card.title, _font(70, bold=True), QColor("#ffffff"))
    _draw_wrapped(painter, QRectF(78, 1135, 900, 120), card.body, _font(31), QColor("#e8f1eb"))


def _poster_palette(poster: QImage | None) -> tuple[QColor, QColor]:
    if not poster or poster.isNull():
        return QColor("#f3efe6"), QColor("#4f8a67")
    samples: list[QColor] = []
    for y in range(0, poster.height(), max(1, poster.height() // 16)):
        for x in range(0, poster.width(), max(1, poster.width() // 16)):
            color = poster.pixelColor(x, y)
            if 45 < color.lightness() < 220 and color.alpha() > 180:
                samples.append(color)
    if not samples:
        return QColor("#f3efe6"), QColor("#4f8a67")
    accent = QColor(
        sum(color.red() for color in samples) // len(samples),
        sum(color.green() for color in samples) // len(samples),
        sum(color.blue() for color in samples) // len(samples),
    )
    background = QColor(
        int(accent.red() * 0.14 + 247 * 0.86),
        int(accent.green() * 0.14 + 244 * 0.86),
        int(accent.blue() * 0.14 + 236 * 0.86),
    )
    if accent.lightness() < 75:
        accent = accent.lighter(180)
    return background, accent


def _mascot_for(category: str) -> QImage | None:
    names = {
        "러닝": "running.png",
        "자전거": "cycling.png",
        "캠핑·레저": "camping.png",
        "행사·이벤트": "events.png",
    }
    path = MASCOT_DIR / names.get(category, "events.png")
    image = QImage(str(path))
    return image if not image.isNull() else None


def _draw_info_card(
    painter: QPainter,
    card: Card,
    index: int,
    background: QColor,
    accent: QColor,
    mascot: QImage | None,
    poster: QImage | None,
) -> None:
    painter.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT, accent.darker(135))
    if poster and not poster.isNull():
        scaled_bg = poster.scaled(
            CARD_WIDTH, CARD_HEIGHT, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        sx = max(0, (scaled_bg.width() - CARD_WIDTH) // 2)
        sy = max(0, (scaled_bg.height() - CARD_HEIGHT) // 2)
        painter.setOpacity(0.48)
        painter.drawImage(
            QRectF(0, 0, CARD_WIDTH, CARD_HEIGHT),
            scaled_bg,
            QRectF(sx, sy, CARD_WIDTH, CARD_HEIGHT),
        )
        painter.setOpacity(1.0)
    painter.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT, QColor(accent.red(), accent.green(), accent.blue(), 96))

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#472415")))
    painter.drawRoundedRect(QRectF(420, 58, 240, 70), 35, 35)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(_font(31, bold=True))
    painter.drawText(QRectF(420, 70, 240, 48), Qt.AlignCenter, f"{index + 1:02d} / 06")

    _draw_wrapped(painter, QRectF(62, 162, 956, 200), card.title, _font(64, bold=True), QColor("#11243a"))
    sections = [section.strip() for section in card.body.split("\n\n") if section.strip()]
    panel_top = 390.0
    available_height = 440.0
    gap = 18.0
    panel_height = min(142.0, (available_height - gap * max(0, len(sections) - 1)) / max(1, len(sections)))
    for section_index, section in enumerate(sections[:4]):
        y = panel_top + section_index * (panel_height + gap)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QBrush(QColor(255, 250, 239, 242)))
        painter.drawRoundedRect(QRectF(72, y, 936, panel_height), 42, 42)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#5b2d18")))
        painter.drawEllipse(QRectF(94, y + 24, 72, 72))
        painter.setPen(QColor("#ffffff"))
        painter.setFont(_font(30, bold=True))
        painter.drawText(QRectF(94, y + 30, 72, 58), Qt.AlignCenter, str(section_index + 1))
        _draw_wrapped(
            painter,
            QRectF(190, y + 22, 780, panel_height - 30),
            section,
            _font(34, bold=True),
            QColor("#13243a"),
        )
    if mascot and not mascot.isNull():
        scaled = mascot.scaled(430, 430, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.setOpacity(1.0)
        painter.drawImage(CARD_WIDTH - scaled.width() - 54, 870, scaled)
        painter.setOpacity(1.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(30, 47, 38, 205)))
    painter.drawRoundedRect(QRectF(70, 1220, 300, 72), 16, 16)
    _draw_wrapped(painter, QRectF(98, 1239, 250, 40), "▲ ACTIVE LOG", _font(25, bold=True), QColor("#ffffff"))


def _write_companion_files(post: dict, output_dir: Path) -> None:
    cards = build_cards(post)
    tags = post.get("tags", [])
    if not tags and post.get("tags_json"):
        import json

        tags = json.loads(post["tags_json"])
    hashtags = " ".join(f"#{re.sub(r'[^0-9A-Za-z가-힣]', '', str(tag))}" for tag in tags if str(tag).strip())
    caption = f"{post.get('title', '')}\n\n{post.get('summary', '')}\n\n{cards[1].body}\n\n{hashtags}".strip()
    (output_dir / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    (output_dir / "업로드-안내.txt").write_text(
        "인스타그램에서 새 게시물 > 여러 장 선택을 누르고 01.png부터 06.png까지 "
        "번호 순서대로 선택하세요. caption.txt를 복사해 본문에 붙여넣고, "
        "출처·일정을 마지막으로 확인한 뒤 게시하세요.\n",
        encoding="utf-8",
    )


def generate_instagram_cards(post: dict, output_dir: Path, poster_path: Path | None = None) -> list[Path]:
    # Font rendering requires a GUI application even when cards are generated
    # from a CLI or test process. The desktop app already provides one.
    gui_app = QGuiApplication.instance() or QGuiApplication([])
    output_dir.mkdir(parents=True, exist_ok=True)
    cards = build_cards(post)
    poster = QImage(str(poster_path)) if poster_path and poster_path.is_file() else None
    background, accent = _poster_palette(poster)
    mascot = _mascot_for(str(post.get("category", "")))
    paths: list[Path] = []
    for index, card in enumerate(cards):
        image = QImage(CARD_WIDTH, CARD_HEIGHT, QImage.Format_ARGB32)
        image.fill(QColor("#ffffff"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        if index == 0:
            _draw_cover(painter, card, poster)
        else:
            _draw_info_card(painter, card, index, background, accent, mascot, poster)
        painter.end()
        path = output_dir / f"{index + 1:02d}.png"
        if not image.save(str(path), "PNG"):
            raise RuntimeError(f"카드 이미지를 저장하지 못했습니다: {path}")
        paths.append(path)
    _write_companion_files(post, output_dir)
    # Keep the locally-created application alive through every paint/save call.
    _ = gui_app
    return paths
