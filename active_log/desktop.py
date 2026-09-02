from __future__ import annotations

import asyncio
import ctypes
import html
import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QStatusBar, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QToolBar, QVBoxLayout, QWidget,
)

from .config import settings
from .db import Database
from .service import AutomationService
from .quality import inspect_post


APP_STYLE = """
QMainWindow, QWidget { background: #f4f7f5; color: #17251c; font-family: "Malgun Gothic"; font-size: 14px; }
QToolBar { background: #123d29; border: 0; spacing: 5px; padding: 8px 12px; }
QToolBar::separator { background: #47705b; width: 1px; margin: 7px 8px; }
QToolBar QToolButton { color: #ffffff; background: transparent; padding: 8px 12px; border-radius: 7px; font-weight: 700; }
QToolBar QToolButton:hover { background: #286246; }
QToolBar QToolButton:pressed { background: #0b2d1d; }
QTableWidget, QLineEdit, QTextEdit, QComboBox { background: #ffffff; color: #17251c; border: 1px solid #bdc9c1; border-radius: 7px; selection-background-color: #dcefe3; selection-color: #123d29; }
QTableWidget { gridline-color: #e1e8e3; alternate-background-color: #f8faf9; }
QTableWidget::item { padding: 6px; }
QTableWidget::item:selected { background: #d7ebdf; color: #123d29; }
QHeaderView::section { background: #e8efea; color: #263c2e; border: 0; border-right: 1px solid #d2ddd5; border-bottom: 1px solid #c4d0c7; padding: 8px 6px; font-weight: 700; }
QLineEdit, QComboBox { min-height: 22px; padding: 7px 9px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 2px solid #278455; }
QTextEdit { padding: 8px; }
QPushButton { background: #176b43; color: #ffffff; border: 1px solid #176b43; border-radius: 7px; padding: 9px 14px; font-weight: 700; }
QPushButton:hover { background: #105535; border-color: #105535; }
QPushButton:disabled { background: #aeb9b2; color: #eef1ef; border-color: #aeb9b2; }
QPushButton[secondary="true"] { background: #ffffff; color: #155f3d; border: 1px solid #7fa28d; }
QPushButton[secondary="true"]:hover { background: #e8f3ec; color: #0d4c2f; }
QPushButton[public="true"] { background: #b54708; color: white; border-color: #b54708; font-size: 15px; padding: 11px 16px; }
QPushButton[public="true"]:hover { background: #93370d; border-color: #93370d; }
QSplitter::handle { background: #dbe4de; }
QSplitter::handle:hover { background: #8eb19a; }
QTabWidget::pane { border: 1px solid #bdc9c1; background: white; }
QTabBar::tab { padding: 8px 16px; background: #e8ece9; }
QTabBar::tab:selected { background: white; color: #155f3d; font-weight: 700; }
QStatusBar { background: #ffffff; color: #425449; border-top: 1px solid #dbe3dd; }
"""


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = Path.cwd()
APP_ICON_PATH = PROJECT_ROOT / "tistory_skin" / "images" / "activelog-app.ico"
SKIN_CSS = "\n".join(
    path.read_text(encoding="utf-8")
    for path in (
        PROJECT_ROOT / "tistory_skin" / "style.css",
        PROJECT_ROOT / "tistory_skin" / "active-log-overrides.css",
    )
    if path.is_file()
)


def _preview_document(title: str, category: str, content: str, image_urls: list[str] | None = None) -> str:
    hero = "".join(
        f"<figure class='post-hero'><img src='{html.escape(url, quote=True)}' "
        f"alt='{html.escape(title or '행사 안내 이미지', quote=True)}'></figure>"
        for url in image_urls or []
    )
    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <style>{SKIN_CSS}
    html,body{{margin:0;background:#fff}}
    .preview-blog{{width:100%;min-height:100vh;background:#fff}}
    .preview-blog .article-header{{position:relative;top:auto;left:auto;transform:none;width:100%;height:400px;background:linear-gradient(125deg,#173d2a,#286344)}}
    .preview-blog .article-header .inner-header{{position:relative;height:100%;max-width:1020px;padding:0 30px}}
    .preview-blog .article-header .box-meta{{left:30px;right:30px}}
    .preview-blog #article-view{{max-width:860px;margin:0 auto;padding-top:54px;background:#fff}}
    .preview-blog .post-hero{{margin:0 0 36px}}
    .preview-blog .post-hero img{{display:block;width:100%;height:auto;border-radius:14px;object-fit:cover}}
    @media(max-width:768px){{
      .preview-blog .article-header{{height:300px}}
      .preview-blog .article-header .inner-header{{padding:0 20px}}
      .preview-blog .article-header .box-meta{{left:20px;right:20px;bottom:32px}}
      .preview-blog #article-view{{padding:30px 18px 45px}}
    }}
    </style></head><body><main class='preview-blog'>
    <div class='article-header'><div class='inner-header'><div class='box-meta'>
      <p class='category'>{html.escape(category or '카테고리')}</p>
      <h2 class='title-article'>{html.escape(title or '제목 없음')}</h2>
      <div class='box-info'><span class='writer'>ACTIVE LOG</span><span class='date'>{datetime.now().strftime('%Y. %m. %d.')}</span></div>
    </div></div></div>
    <div class='article-view' id='article-view'>{hero}{content or '<p>본문을 입력하면 여기에 표시됩니다.</p>'}</div>
    </main></body></html>"""


class PublishWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, service: AutomationService, post_id: int):
        super().__init__()
        self.service = service
        self.post_id = post_id

    def run(self) -> None:
        try:
            url = asyncio.run(self.service.publish_public(self.post_id))
            self.succeeded.emit(url)
        except Exception as exc:
            self.failed.emit(str(exc))


class GenerateWorker(QThread):
    succeeded = Signal(int)
    failed = Signal(str)

    def __init__(self, service: AutomationService):
        super().__init__()
        self.service = service

    def run(self) -> None:
        try:
            self.succeeded.emit(self.service.create_draft())
        except Exception as exc:
            self.failed.emit(str(exc))


class DesktopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database(settings.database_path)
        self.service = AutomationService(settings, self.db)
        self.current_id: int | None = None
        self.worker: PublishWorker | None = None
        self.generation_worker: GenerateWorker | None = None
        self.login_process: QProcess | None = None
        self.dirty = False
        self.loading = False
        self.setWindowTitle("Active Log 콘텐츠 스튜디오")
        if APP_ICON_PATH.is_file():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(1500, 900)
        self.setMinimumSize(1050, 680)
        self._build_ui()
        self.refresh_posts()

    def _build_ui(self) -> None:
        toolbar = QToolBar("도구")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(toolbar)
        brand = QLabel("  ACTIVE LOG  ")
        brand.setStyleSheet("color:white;background:#123d29;font-size:16px;font-weight:800;padding-right:10px")
        toolbar.addWidget(brand)
        toolbar.addSeparator()
        for label, slot in (("새 글 작성", self.generate_post), ("티스토리 로그인", self.login)):
            action = QAction(label, self)
            action.triggered.connect(slot)
            if label == "새 글 작성":
                action.setShortcut("Ctrl+N")
                self.generate_action = action
            toolbar.addAction(action)

        root = QSplitter(Qt.Horizontal)
        root.setChildrenCollapsible(False)
        self.setCentralWidget(root)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(14, 14, 8, 14)
        heading = QLabel("게시글")
        heading.setStyleSheet("font-size:20px;font-weight:700")
        left_layout.addWidget(heading)
        self.search = QLineEdit()
        self.search.setPlaceholderText("제목·카테고리 검색")
        self.search.textChanged.connect(self.apply_filters)
        left_layout.addWidget(self.search)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["전체 상태", "검토 대기", "게시 중", "공개 게시", "실패"])
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        left_layout.addWidget(self.status_filter)
        self.order_filter = QComboBox()
        self.order_filter.addItem("순번순 (1 → N)", True)
        self.order_filter.addItem("최신순 (N → 1)", False)
        self.order_filter.currentIndexChanged.connect(lambda: self.refresh_posts(self.current_id))
        left_layout.addWidget(self.order_filter)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["순번", "제목", "게시 여부", "카테고리", "게시 일시"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(2, 75)
        self.table.setColumnWidth(3, 105)
        self.table.setColumnWidth(4, 125)
        self.table.itemSelectionChanged.connect(self.load_selected)
        left_layout.addWidget(self.table)
        root.addWidget(left)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(8, 14, 8, 14)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(9)
        self.title = QLineEdit()
        self.topic_key = QLineEdit()
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(["러닝", "자전거", "캠핑·레저", "행사·이벤트"])
        self.category.currentTextChanged.connect(self.schedule_preview)
        self.summary = QTextEdit()
        self.summary.setMaximumHeight(80)
        self.tags = QLineEdit()
        self.sources = QTextEdit()
        self.sources.setMaximumHeight(65)
        form.addRow("제목", self.title)
        form.addRow("식별 키", self.topic_key)
        form.addRow("카테고리", self.category)
        form.addRow("요약", self.summary)
        form.addRow("태그 (쉼표 구분)", self.tags)
        form.addRow("출처 (줄 구분)", self.sources)
        editor_layout.addLayout(form)
        editor_layout.addWidget(QLabel("본문 HTML"))
        self.body = QTextEdit()
        self.body.setAcceptRichText(False)
        self.body.setPlaceholderText("티스토리에 게시할 본문 HTML을 입력하세요.")
        self.body.textChanged.connect(self.schedule_preview)
        self.title.textChanged.connect(self.schedule_preview)
        for widget in (self.title, self.topic_key, self.summary, self.body, self.tags, self.sources):
            widget.textChanged.connect(self.mark_dirty)
        self.category.currentTextChanged.connect(self.mark_dirty)
        editor_layout.addWidget(self.body, 1)
        save_button = QPushButton("대기 글로 저장")
        save_button.clicked.connect(self.save_post)
        editor_layout.addWidget(save_button)
        actions = QHBoxLayout()
        self.check_button = QPushButton("게시 전 검사")
        self.check_button.setProperty("secondary", True)
        self.check_button.clicked.connect(self.show_quality_report)
        self.retry_button = QPushButton("실패 글 다시 대기")
        self.retry_button.setProperty("secondary", True)
        self.retry_button.clicked.connect(self.requeue_current)
        self.open_button = QPushButton("티스토리에서 열기")
        self.open_button.setProperty("secondary", True)
        self.open_button.clicked.connect(self.open_published)
        self.republish_button = QPushButton("다시 공개 게시")
        self.republish_button.setProperty("secondary", True)
        self.republish_button.clicked.connect(self.republish_current)
        self.delete_button = QPushButton("목록에서 삭제")
        self.delete_button.setProperty("secondary", True)
        self.delete_button.clicked.connect(self.delete_current)
        actions.addWidget(self.check_button)
        actions.addWidget(self.retry_button)
        actions.addWidget(self.open_button)
        actions.addWidget(self.republish_button)
        actions.addWidget(self.delete_button)
        editor_layout.addLayout(actions)
        self.post_detail = QLabel("글을 선택하면 게시 상태와 오류가 표시됩니다.")
        self.post_detail.setWordWrap(True)
        self.post_detail.setStyleSheet("color:#637067;padding:6px 2px")
        editor_layout.addWidget(self.post_detail)
        self.publish_button = QPushButton("검토 완료 · 티스토리에 공개 게시")
        self.publish_button.setProperty("public", True)
        self.publish_button.clicked.connect(self.publish)
        editor_layout.addWidget(self.publish_button)
        root.addWidget(editor)

        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(8, 14, 14, 14)
        preview_header = QHBoxLayout()
        label = QLabel("게시 전 미리보기")
        label.setStyleSheet("font-size:20px;font-weight:700")
        preview_header.addWidget(label)
        preview_header.addStretch()
        desktop = QPushButton("PC")
        mobile = QPushButton("모바일")
        desktop.setToolTip("넓은 화면 미리보기")
        mobile.setToolTip("390px 모바일 화면 미리보기")
        desktop.clicked.connect(lambda: self.set_preview_width(False))
        mobile.clicked.connect(lambda: self.set_preview_width(True))
        preview_header.addWidget(desktop)
        preview_header.addWidget(mobile)
        preview_layout.addLayout(preview_header)
        self.preview_frame = QFrame()
        frame_layout = QHBoxLayout(self.preview_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setAlignment(Qt.AlignHCenter)
        self.preview = QWebEngineView()
        frame_layout.addWidget(self.preview)
        preview_layout.addWidget(self.preview_frame, 1)
        root.addWidget(preview_panel)
        root.setSizes([340, 480, 680])

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(250)
        self.preview_timer.timeout.connect(self.update_preview)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("준비됨")
        self.update_preview()

    def refresh_posts(self, select_id: int | None = None) -> None:
        oldest_first = bool(self.order_filter.currentData()) if hasattr(self, "order_filter") else False
        rows = self.db.list_posts(200, oldest_first=oldest_first)
        sequence_by_id = {
            post_id: sequence
            for sequence, post_id in enumerate(sorted(int(post["id"]) for post in rows), start=1)
        }
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        selected_row = None
        for row_index, post in enumerate(rows):
            status_labels = {
                "draft": "미게시 · 검토 대기", "publishing": "게시 중",
                "private": "비공개 게시 완료", "public": "공개 게시 완료", "failed": "게시 실패",
            }
            published_text = ""
            if post.get("published_at"):
                try:
                    published_text = datetime.fromisoformat(post["published_at"]).strftime("%Y.%m.%d %H:%M")
                except ValueError:
                    published_text = str(post["published_at"])
            values = (
                sequence_by_id[int(post["id"])], post["title"], status_labels.get(post["status"], post["status"]),
                post["category"], published_text,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.UserRole, int(post["id"]))
                if column == 2:
                    colors = {"draft": "#1f6b45", "publishing": "#a56800", "private": "#315a9b", "public": "#6b3fa0", "failed": "#b42318"}
                    item.setData(Qt.UserRole, post["status"])
                    item.setForeground(QColor(colors.get(post["status"], "#4b5650")))
                self.table.setItem(row_index, column, item)
            if select_id == post["id"]:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row is not None:
            self.table.selectRow(selected_row)
        self.apply_filters()
        self.statusBar().showMessage(f"게시글 {len(rows)}개 · 대기 {self.db.count_drafts()}개")

    def load_selected(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        id_item = self.table.item(items[0].row(), 0)
        selected_id = int(id_item.data(Qt.UserRole))
        if self.dirty and self.current_id is not None and selected_id != self.current_id:
            answer = QMessageBox.question(self, "저장하지 않은 변경", "변경사항을 저장하고 다른 글을 열까요?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel:
                self.refresh_posts(self.current_id)
                return
            if answer == QMessageBox.Save and not self.save_post():
                self.refresh_posts(self.current_id)
                return
        post = self.db.get_post(selected_id)
        if not post:
            return
        self.loading = True
        self.current_id = int(post["id"])
        self.title.setText(post["title"])
        self.topic_key.setText(post["topic_key"])
        self.category.setCurrentText(post["category"])
        self.summary.setPlainText(post["summary"])
        self.body.setPlainText(post["content_html"])
        self.tags.setText(", ".join(json.loads(post["tags_json"])))
        source_values = json.loads(post["sources_json"])
        self.sources.setPlainText("\n".join(
            source.get("url", "") if isinstance(source, dict) else str(source)
            for source in source_values
        ))
        self.loading = False
        self.dirty = False
        self.update_post_actions(post)
        self.update_preview()

    def new_post(self) -> None:
        if self.dirty and QMessageBox.question(self, "저장하지 않은 변경", "변경사항을 버리고 새 글을 작성할까요?") != QMessageBox.Yes:
            return
        self.loading = True
        self.current_id = None
        self.table.clearSelection()
        for widget in (self.title, self.topic_key, self.summary, self.body, self.tags, self.sources):
            widget.clear()
        self.category.setCurrentIndex(0)
        self.loading = False
        self.dirty = False
        self.update_post_actions(None)
        self.update_preview()
        self.title.setFocus()

    def _form_data(self) -> dict:
        title = self.title.text().strip()
        topic_key = self.topic_key.text().strip()
        summary = self.summary.toPlainText().strip()
        content = self.body.toPlainText().strip()
        sources = [value.strip() for value in self.sources.toPlainText().splitlines() if value.strip()]
        if not all((title, topic_key, summary, content, sources)):
            raise ValueError("제목, 식별 키, 요약, 본문, 출처를 모두 입력하세요.")
        return {
            "title": title, "topic_key": topic_key, "category": self.category.currentText().strip(),
            "summary": summary, "content_html": content,
            "tags": [value.strip() for value in self.tags.text().split(",") if value.strip()],
            "sources": sources,
        }

    def save_post(self) -> bool:
        try:
            data = self._form_data()
            if self.current_id is None:
                self.current_id = self.db.save_post(data)
            else:
                self.db.update_post(self.current_id, data)
            self.refresh_posts(self.current_id)
            self.dirty = False
            self.statusBar().showMessage("저장했습니다.", 5000)
            return True
        except Exception as exc:
            QMessageBox.warning(self, "저장할 수 없음", str(exc))
            return False

    def mark_dirty(self) -> None:
        if not self.loading:
            self.dirty = True
            self.statusBar().showMessage("저장하지 않은 변경사항이 있습니다.")

    def apply_filters(self) -> None:
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        labels = {"검토 대기": "draft", "게시 중": "publishing", "공개 게시": "public", "실패": "failed"}
        status = labels.get(self.status_filter.currentText(), "") if hasattr(self, "status_filter") else ""
        for row in range(self.table.rowCount()):
            haystack = " ".join(self.table.item(row, column).text().lower() for column in (1, 3))
            row_status = self.table.item(row, 2).data(Qt.UserRole) or self.table.item(row, 2).text()
            self.table.setRowHidden(row, bool((query and query not in haystack) or (status and status != row_status)))

    def current_form_post(self) -> dict:
        data = self._form_data()
        return data

    def quality_issues(self):
        return inspect_post(self.current_form_post(), PROJECT_ROOT)

    def show_quality_report(self) -> bool:
        try:
            issues = self.quality_issues()
        except Exception as exc:
            QMessageBox.warning(self, "검사할 수 없음", str(exc))
            return False
        if not issues:
            QMessageBox.information(self, "게시 전 검사", "필수 검사와 권장 검사를 모두 통과했습니다.")
            return True
        text = "\n".join(f"{'오류' if issue.level == 'error' else '주의'} · {issue.message}" for issue in issues)
        QMessageBox.warning(self, "게시 전 검사 결과", text)
        return not any(issue.level == "error" for issue in issues)

    def update_post_actions(self, post: dict | None) -> None:
        status = post.get("status") if post else None
        self.retry_button.setVisible(status == "failed")
        self.open_button.setVisible(bool(post and post.get("tistory_url")))
        self.republish_button.setVisible(status == "public")
        self.delete_button.setEnabled(bool(post) and status != "publishing")
        self.publish_button.setEnabled(status == "draft")
        self.publish_button.setText(
            "검토 완료 · 티스토리에 공개 게시" if status == "draft" else "공개 게시할 검토 대기 글을 선택하세요"
        )
        if not post:
            self.post_detail.setText("새 글을 작성 중입니다.")
        elif status == "failed":
            self.post_detail.setText(f"게시 실패 · {post.get('error') or '오류 정보 없음'}")
            self.post_detail.setStyleSheet("color:#b42318;padding:6px 2px")
        else:
            status_label = {"draft": "검토 대기", "publishing": "게시 중", "private": "비공개 게시 완료", "public": "공개 게시 완료", "failed": "게시 실패"}.get(status, status)
            self.post_detail.setText(f"상태: {status_label}" + (f" · {post.get('tistory_url')}" if post.get("tistory_url") else ""))
            self.post_detail.setStyleSheet("color:#637067;padding:6px 2px")

    def requeue_current(self) -> None:
        if self.current_id is None:
            return
        self.db.requeue_post(self.current_id)
        self.refresh_posts(self.current_id)
        self.statusBar().showMessage("게시 대기 상태로 변경했습니다.", 5000)

    def republish_current(self) -> None:
        if self.current_id is None:
            return
        if self.dirty and not self.save_post():
            return
        if not self.show_quality_report():
            return
        if QMessageBox.question(
            self,
            "다시 공개 게시",
            "현재 티스토리 글은 그대로 두고, 수정된 내용과 이미지를 새 공개 글로 다시 게시할까요?",
        ) != QMessageBox.Yes:
            return
        self.db.requeue_post(self.current_id)
        self.refresh_posts(self.current_id)
        self._start_publish()

    def open_published(self) -> None:
        post = self.db.get_post(self.current_id) if self.current_id else None
        if post and post.get("tistory_url"):
            QDesktopServices.openUrl(QUrl(post["tistory_url"]))

    def delete_current(self) -> None:
        if self.current_id is None:
            return
        post = self.db.get_post(self.current_id)
        if not post:
            return
        detail = "이 작업은 되돌릴 수 없습니다."
        if post.get("status") in {"private", "public"}:
            detail += "\n티스토리에 게시된 글은 삭제되지 않고 앱의 기록만 제거됩니다."
        if QMessageBox.question(
            self,
            "게시글 삭제",
            f"'{post['title']}'을 목록에서 삭제할까요?\n\n{detail}",
        ) != QMessageBox.Yes:
            return
        try:
            self.db.delete_post(self.current_id)
            self.current_id = None
            self.dirty = False
            self.new_post()
            self.refresh_posts()
            self.statusBar().showMessage("게시글을 목록에서 삭제했습니다.", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "삭제할 수 없음", str(exc))

    def generate_post(self) -> None:
        if self.dirty and QMessageBox.question(
            self,
            "저장하지 않은 변경",
            "변경사항을 버리고 새 게시글을 자동 생성할까요?",
        ) != QMessageBox.Yes:
            return
        self._start_generation()

    def _start_generation(self) -> None:
        if self.generation_worker and self.generation_worker.isRunning():
            QMessageBox.information(self, "게시글 생성 중", "이미 새 게시글을 생성하고 있습니다.")
            return
        self.generation_worker = GenerateWorker(self.service)
        self.generation_worker.succeeded.connect(self.generation_succeeded)
        self.generation_worker.failed.connect(self.generation_failed)
        self.generate_action.setEnabled(False)
        self.generation_worker.start()
        self.statusBar().showMessage("공식 행사 정보와 포스터로 새 게시글을 작성하는 중…")

    def generation_succeeded(self, post_id: int) -> None:
        self.generate_action.setEnabled(True)
        self.refresh_posts(post_id)
        self.statusBar().showMessage("새 게시글을 생성해 검토 대기 상태로 저장했습니다.", 8000)

    def generation_failed(self, message: str) -> None:
        self.generate_action.setEnabled(True)
        QMessageBox.warning(self, "게시글 생성 실패", message)

    def schedule_preview(self) -> None:
        self.preview_timer.start()

    def update_preview(self) -> None:
        image_urls = [
            path.resolve().as_uri()
            for path in self.service.find_images(self.topic_key.text().strip())
        ]
        self.preview.setHtml(
            _preview_document(
                self.title.text(), self.category.currentText(), self.body.toPlainText(), image_urls
            ),
            PROJECT_ROOT.as_uri() + "/",
        )

    def set_preview_width(self, mobile: bool) -> None:
        if mobile:
            self.preview.setMinimumWidth(390)
            self.preview.setMaximumWidth(390)
        else:
            self.preview.setMinimumWidth(0)
            self.preview.setMaximumWidth(16777215)

    def login(self) -> None:
        if self.login_process and self.login_process.state() != QProcess.NotRunning:
            QMessageBox.information(self, "로그인 진행 중", "이미 로그인 창이 열려 있습니다.")
            return
        self.login_process = QProcess(self)
        self.login_process.finished.connect(lambda: self.statusBar().showMessage("로그인 프로세스가 종료되었습니다.", 5000))
        bundled_python = RUNTIME_ROOT / ".python" / "python.exe"
        login_program = str(bundled_python) if bundled_python.is_file() else sys.executable
        self.login_process.setWorkingDirectory(str(RUNTIME_ROOT))
        self.login_process.start(login_program, ["-m", "active_log.main", "login"])
        self.statusBar().showMessage("Chrome에서 카카오 로그인을 완료하세요.")

    def publish(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "게시 진행 중", "현재 게시 작업이 끝날 때까지 기다려 주세요.")
            return
        if self.current_id is None:
            QMessageBox.information(self, "게시할 글 선택", "먼저 글을 저장하거나 목록에서 선택하세요.")
            return
        if not self.save_post() or not self.current_id:
            return
        if not self.show_quality_report():
            return
        if QMessageBox.question(
            self,
            "공개 게시 확인",
            "검토를 마친 글을 티스토리에 즉시 공개할까요?\n게시 직후 독자에게 노출될 수 있습니다.",
        ) != QMessageBox.Yes:
            return
        self._start_publish()

    def _start_publish(self) -> None:
        self.worker = PublishWorker(self.service, self.current_id)
        self.worker.succeeded.connect(self.publish_succeeded)
        self.worker.failed.connect(self.publish_failed)
        self.publish_button.setEnabled(False)
        self.worker.start()
        self.statusBar().showMessage("티스토리에 공개 게시 중…")

    def publish_succeeded(self, url: str) -> None:
        self.refresh_posts(self.current_id)
        QMessageBox.information(self, "게시 완료", f"공개 게시를 완료했습니다.\n{url}")

    def publish_failed(self, message: str) -> None:
        self.refresh_posts(self.current_id)
        QMessageBox.critical(self, "게시 실패", message)

    def closeEvent(self, event) -> None:
        if self.generation_worker and self.generation_worker.isRunning():
            QMessageBox.information(self, "게시글 생성 중", "새 게시글 생성이 끝날 때까지 기다려 주세요.")
            event.ignore()
            return
        if self.dirty and QMessageBox.question(
            self, "저장하지 않은 변경", "저장하지 않은 변경사항이 있습니다. 앱을 종료할까요?"
        ) != QMessageBox.Yes:
            event.ignore()
            return
        event.accept()


def run() -> None:
    if sys.platform == "win32":
        # Give Windows a stable identity so pinned taskbar shortcuts retain the app icon.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ActiveLog.ContentStudio"
        )
    app = QApplication(sys.argv)
    app.setApplicationName("Active Log 콘텐츠 스튜디오")
    if APP_ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setStyleSheet(APP_STYLE)
    window = DesktopWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    run()
