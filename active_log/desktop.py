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
    QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QToolBar, QVBoxLayout, QWidget,
)

from .config import settings
from .db import Database
from .official_generator import CATEGORIES
from .publisher import TistoryPublisher
from .service import AutomationService
from .quality import inspect_post


APP_STYLE = """
QMainWindow, QWidget { background: #f7f8f4; color: #24352b; font-family: "Malgun Gothic"; font-size: 14px; }
QLabel { background: transparent; }
QToolBar { background: #284738; border: 0; spacing: 6px; padding: 9px 14px; }
QToolBar::separator { background: #587264; width: 1px; margin: 7px 9px; }
QToolBar QToolButton { color: #ffffff; background: transparent; padding: 9px 13px; border-radius: 10px; font-weight: 700; }
QToolBar QToolButton:hover { background: #3b5d4c; }
QToolBar QToolButton:pressed { background: #193426; }
QTableWidget, QLineEdit, QTextEdit, QComboBox { background: #ffffff; color: #24352b; border: 1px solid #d9e1db; border-radius: 10px; selection-background-color: #e6f2e9; selection-color: #214832; }
QTableWidget { gridline-color: #edf1ee; alternate-background-color: #fbfcfa; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #eff2ef; }
QTableWidget::item:selected { background: #e4f1e8; color: #214832; }
QHeaderView::section { background: #f4f7f4; color: #53635a; border: 0; border-bottom: 1px solid #e1e7e2; padding: 10px 7px; font-weight: 700; }
QLineEdit, QComboBox { min-height: 24px; padding: 8px 11px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 2px solid #62a47e; }
QTextEdit { padding: 10px; }
QPushButton { background: #347b56; color: #ffffff; border: 1px solid #347b56; border-radius: 10px; padding: 10px 16px; font-weight: 700; }
QPushButton:hover { background: #286747; border-color: #286747; }
QPushButton:pressed { background: #20553a; border-color: #20553a; }
QPushButton:disabled { background: #e5e9e6; color: #9ba69f; border-color: #e5e9e6; }
QPushButton[secondary="true"] { background: #ffffff; color: #3d6650; border: 1px solid #cbd8cf; }
QPushButton[secondary="true"]:hover { background: #f0f6f2; color: #28543c; border-color: #9eb9a8; }
QPushButton[public="true"] { background: #d47445; color: white; border-color: #d47445; font-size: 15px; padding: 12px 18px; }
QPushButton[public="true"]:hover { background: #bf6036; border-color: #bf6036; }
QSplitter::handle { background: #eef1ee; width: 8px; }
QSplitter::handle:hover { background: #c9d9ce; }
QTabWidget::pane { border: 1px solid #dce4de; background: white; border-radius: 10px; }
QTabBar::tab { padding: 9px 17px; background: #eef2ef; border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:selected { background: white; color: #347b56; font-weight: 700; }
QStatusBar { background: #ffffff; color: #66736b; border-top: 1px solid #e5eae6; }
QWidget#sideNav { background:#284738; }
QWidget#sideNav QLabel { color:white; background:transparent; }
QWidget#sideNav QPushButton { background:transparent; color:#dce8e0; border:0; border-radius:11px; text-align:left; padding:12px 15px; font-weight:600; }
QWidget#sideNav QPushButton:hover { background:#365746; color:#ffffff; }
QWidget#sideNav QPushButton[active="true"] { background:#f2f6f2; color:#244b35; font-weight:800; }
QFrame#summaryCard { background:white; border:1px solid #e2e8e3; border-radius:16px; }
QWidget#workspacePanel { background:white; border:1px solid #e3e9e4; border-radius:16px; }
QLabel#summaryNumber { font-size:32px; font-weight:800; color:#347b56; }
QLabel#summaryCaption { color:#6b786f; font-size:13px; }
QLabel#pageTitle { font-size:26px; font-weight:800; color:#21372a; }
QLabel#sectionTitle { font-size:18px; font-weight:800; color:#2b3c31; }
QLabel#mutedText { color:#718078; }
QLabel#brandTitle { font-size:20px; font-weight:900; letter-spacing:1px; }
QLabel#brandSubtitle { color:#bcd0c3; font-size:11px; }
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
    images = image_urls or []
    hero = "".join(
        f"<figure class='imageblock alignCenter'><span><img src='{html.escape(url, quote=True)}' "
        f"alt='{html.escape(title or '행사 안내 이미지', quote=True)}'></figure>"
        for url in images
    )
    hero = hero.replace("</figure>", "</span></figure>")
    thumbnail = html.escape(images[0], quote=True) if images else ""
    logo_url = (PROJECT_ROOT / "tistory_skin" / "images" / "activelog-logo-v2.png").resolve().as_uri()
    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <style>{SKIN_CSS}
    html,body{{margin:0;background:#fff}}
    .preview-only-search{{pointer-events:none}}
    .article-header{{background-image:linear-gradient(rgba(20,25,22,.42),rgba(20,25,22,.42)),url('{thumbnail}') !important;background-color:#315540}}
    .imageblock img{{display:block;max-width:100%;height:auto;margin:0 auto}}
    </style></head><body id='tt-body-page' class='headerslogundisplayon headerbannerdisplayon listmorenumber listmorebuttonmobile use-menu-topnavnone-wrp'>
    <div id='wrap' class='wrap-right'>
    <header id='custom-header'><div class='header-top-wrap'><div class='header-top-inner'>
      <div class='brand'><h1 class='logo'><a>ACTIVELOG</a></h1><div class='tagline'>러닝·자전거·캠핑·축제 일정을 한눈에 정리합니다.</div></div>
      <div class='top-right-menu'><ul class='utility-links'><li><a>소개</a></li><li><a>방명록</a></li></ul><div class='search-box preview-only-search'><input placeholder='검색어 입력'><button>🔍</button></div></div>
    </div></div><nav class='category-bar'><div class='category-inner'><a class='home-btn'>⌂</a><div class='category-list-wrap'><ul class='tt_category'><li><ul class='category_list'><li><a class='link_item'>러닝</a></li><li><a class='link_item'>자전거</a></li><li><a class='link_item'>캠핑·레저</a></li><li><a class='link_item'>행사·이벤트</a></li></ul></li></ul></div></div></nav></header>
    <div id='container'><main class='main'><div class='area-main'><div class='area-view'>
    <div class='article-header'><div class='inner-header'><div class='box-meta'>
      <p class='category'>{html.escape(category or '카테고리')}</p>
      <h2 class='title-article'>{html.escape(title or '제목 없음')}</h2>
      <div class='box-info'><span class='writer'>액티브로그</span><span class='date'>{datetime.now().strftime('%Y. %m. %d. %H:%M')}</span></div>
    </div></div></div>
    <div class='article-view' id='article-view'><div class='tt_article_useless_p_margin contents_style'>{hero}{content or '<p>본문을 입력하면 여기에 표시됩니다.</p>'}</div></div>
    </div></div><aside class='area-aside'><div class='box-profile'><div class='inner-box'><img src='{logo_url}' class='img-profile' alt='ACTIVELOG'><p class='tit-g'>액티브로그</p><p class='text-profile'>마라톤·라이딩·캠핑·지역 축제의 일정과 접수 정보를 정리합니다.</p><button class='button-subscription'>구독하기</button></div></div></aside></main></div></div>
    </body></html>"""


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

    def __init__(self, service: AutomationService, category: str | None):
        super().__init__()
        self.service = service
        self.category = category

    def run(self) -> None:
        try:
            self.succeeded.emit(self.service.create_draft(self.category))
        except Exception as exc:
            self.failed.emit(str(exc))


class TistoryPostsWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, service: AutomationService):
        super().__init__()
        self.service = service

    def run(self) -> None:
        try:
            publisher = TistoryPublisher(
                self.service.config.blog_name,
                self.service.config.tistory_profile_dir,
                self.service.config.tistory_headless,
            )
            self.succeeded.emit(asyncio.run(publisher.list_posts(50)))
        except Exception as exc:
            self.failed.emit(str(exc))


class TistoryDeleteWorker(QThread):
    succeeded = Signal(int)
    failed = Signal(str)

    def __init__(self, service: AutomationService, post_id: int):
        super().__init__()
        self.service = service
        self.post_id = post_id

    def run(self) -> None:
        try:
            publisher = TistoryPublisher(
                self.service.config.blog_name,
                self.service.config.tistory_profile_dir,
                self.service.config.tistory_headless,
            )
            asyncio.run(publisher.delete_post(self.post_id))
            self.succeeded.emit(self.post_id)
        except Exception as exc:
            self.failed.emit(str(exc))


class DesktopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database(settings.database_path)
        self.service = AutomationService(settings, self.db)
        self.current_id: int | None = None
        self.current_remote_post: dict | None = None
        self.remote_posts: list[dict] = []
        self.worker: PublishWorker | None = None
        self.generation_worker: GenerateWorker | None = None
        self.tistory_posts_worker: TistoryPostsWorker | None = None
        self.tistory_delete_worker: TistoryDeleteWorker | None = None
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
        self.generate_action = QAction("새 글 작성", self)
        self.generate_action.setShortcut("Ctrl+N")
        self.generate_action.triggered.connect(self.generate_post)
        self.addAction(self.generate_action)
        self.generation_category = QComboBox()
        self.generation_category.addItem("전체 카테고리에서 찾기", None)
        for category in CATEGORIES:
            self.generation_category.addItem(category, category)
        self.generation_category.setToolTip("새 글에서 찾을 카테고리를 선택하세요")

        content_page = QWidget()
        content_page_layout = QVBoxLayout(content_page)
        content_page_layout.setContentsMargins(24, 22, 24, 18)
        content_page_layout.setSpacing(14)
        content_header = QHBoxLayout()
        content_heading = QVBoxLayout()
        self.content_title = QLabel("글 관리")
        self.content_title.setObjectName("pageTitle")
        self.content_description = QLabel("새 글부터 티스토리에 게시된 글까지 한곳에서 편하게 확인하세요.")
        self.content_description.setObjectName("mutedText")
        content_heading.addWidget(self.content_title)
        content_heading.addWidget(self.content_description)
        content_header.addLayout(content_heading)
        content_header.addStretch()
        content_new_button = QPushButton("+ 새 글 만들기")
        content_new_button.clicked.connect(self.open_create_page)
        content_header.addWidget(content_new_button)
        content_page_layout.addLayout(content_header)
        root = QSplitter(Qt.Horizontal)
        root.setChildrenCollapsible(False)
        content_page_layout.addWidget(root)

        left = QWidget()
        left.setObjectName("workspacePanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 18, 14, 18)
        left_layout.setSpacing(10)
        heading = QLabel("내 글")
        heading.setObjectName("sectionTitle")
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
        self.order_filter.hide()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["순번", "제목", "상태", "조회수"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 70)
        self.table.itemSelectionChanged.connect(self.load_selected)
        left_layout.addWidget(self.table)
        root.addWidget(left)

        editor = QWidget()
        self.editor_panel = editor
        editor.setObjectName("workspacePanel")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(14, 18, 14, 18)
        editor_layout.setSpacing(10)
        editor_heading = QLabel("내용 다듬기")
        editor_heading.setObjectName("sectionTitle")
        editor_layout.addWidget(editor_heading)
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
        form.addRow("카테고리", self.category)
        form.addRow("요약", self.summary)
        form.addRow("식별 키", self.topic_key)
        form.addRow("태그 (쉼표 구분)", self.tags)
        form.addRow("출처 (줄 구분)", self.sources)
        editor_layout.addLayout(form)
        self.body_label = QLabel("본문 HTML")
        editor_layout.addWidget(self.body_label)
        self.body = QTextEdit()
        self.body.setAcceptRichText(False)
        self.body.setPlaceholderText("티스토리에 게시할 본문 HTML을 입력하세요.")
        self.body.textChanged.connect(self.schedule_preview)
        self.title.textChanged.connect(self.schedule_preview)
        for widget in (self.title, self.topic_key, self.summary, self.body, self.tags, self.sources):
            widget.textChanged.connect(self.mark_dirty)
        self.category.currentTextChanged.connect(self.mark_dirty)
        editor_layout.addWidget(self.body, 1)
        self.advanced_widgets = [self.topic_key, self.tags, self.sources, self.body, self.body_label]
        for widget in (self.topic_key, self.tags, self.sources):
            label = form.labelForField(widget)
            if label:
                self.advanced_widgets.append(label)
        self.advanced_button = QPushButton("고급 옵션")
        self.advanced_button.setProperty("secondary", True)
        self.advanced_button.clicked.connect(self.toggle_advanced_editor)
        editor_layout.addWidget(self.advanced_button)
        self.save_button = QPushButton("저장")
        self.save_button.setProperty("secondary", True)
        self.save_button.clicked.connect(self.save_post)
        editor_layout.addWidget(self.save_button)
        actions = QHBoxLayout()
        self.check_button = QPushButton("게시 전 검사")
        self.check_button.setProperty("secondary", True)
        self.check_button.clicked.connect(self.show_quality_report)
        self.retry_button = QPushButton("게시 다시 시도")
        self.retry_button.setProperty("secondary", True)
        self.retry_button.clicked.connect(self.retry_failed_publish)
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
        self.check_button.hide()
        self.republish_button.hide()
        self.post_detail = QLabel("글을 선택하면 게시 상태와 오류가 표시됩니다.")
        self.post_detail.setWordWrap(True)
        self.post_detail.setObjectName("mutedText")
        self.post_detail.setStyleSheet("padding:6px 2px")
        editor_layout.addWidget(self.post_detail)
        self.publish_button = QPushButton("검토 완료 · 티스토리에 공개 게시")
        self.publish_button.setProperty("public", True)
        self.publish_button.clicked.connect(self.publish)
        editor_layout.addWidget(self.publish_button)
        editor_layout.addStretch(1)
        root.addWidget(editor)

        preview_panel = QWidget()
        preview_panel.setObjectName("workspacePanel")
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(14, 18, 18, 18)
        preview_layout.setSpacing(10)
        preview_header = QHBoxLayout()
        label = QLabel("티스토리 미리보기")
        label.setObjectName("sectionTitle")
        preview_header.addWidget(label)
        preview_header.addStretch()
        self.edit_toggle_button = QPushButton("내용 수정")
        self.edit_toggle_button.setProperty("secondary", True)
        self.edit_toggle_button.clicked.connect(self.toggle_editor_panel)
        self.preview_primary_button = QPushButton("게시")
        self.preview_primary_button.clicked.connect(self.perform_preview_action)
        preview_header.addWidget(self.edit_toggle_button)
        preview_header.addWidget(self.preview_primary_button)
        desktop = QPushButton("PC")
        mobile = QPushButton("모바일")
        desktop.setProperty("secondary", True)
        mobile.setProperty("secondary", True)
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
        self.content_splitter = root
        self.editor_panel.hide()
        root.setSizes([420, 0, 1070])

        self.pages = QStackedWidget()
        dashboard = self._build_dashboard_page()
        remote_posts = self._build_tistory_posts_page()
        channels = self._build_channels_page()
        settings_page = self._build_settings_page()
        self.pages.addWidget(dashboard)
        self.pages.addWidget(content_page)
        self.pages.addWidget(remote_posts)
        self.pages.addWidget(channels)
        self.pages.addWidget(settings_page)

        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        side = QWidget()
        side.setObjectName("sideNav")
        side.setFixedWidth(220)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(16, 24, 16, 18)
        side_layout.setSpacing(7)
        brand = QLabel("ACTIVE LOG")
        brand.setObjectName("brandTitle")
        brand.setContentsMargins(10, 0, 0, 0)
        side_layout.addWidget(brand)
        brand_subtitle = QLabel("콘텐츠를 한눈에, 가볍게")
        brand_subtitle.setObjectName("brandSubtitle")
        brand_subtitle.setContentsMargins(10, 0, 0, 18)
        side_layout.addWidget(brand_subtitle)
        self.nav_buttons = []
        for label, handler in (
            ("⌂   홈", lambda: self.show_page(0)),
            ("✎   글 관리", lambda: self.open_post_list("전체 상태")),
            ("✓   게시된 글", self.show_tistory_posts),
            ("◉   채널 연결", lambda: self.show_page(3)),
            ("⚙   설정", lambda: self.show_page(4)),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            side_layout.addWidget(button)
            self.nav_buttons.append(button)
        side_layout.addStretch()
        safe_note = QLabel("● 자동 게시 꺼짐\n  필요한 글만 직접 게시해요")
        safe_note.setStyleSheet("color:#bdd3c4;font-size:12px;padding:12px 10px")
        side_layout.addWidget(safe_note)
        shell_layout.addWidget(side)
        shell_layout.addWidget(self.pages, 1)
        self.setCentralWidget(shell)
        self.show_page(0)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(250)
        self.preview_timer.timeout.connect(self.update_preview)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("준비됨")
        self.set_preview_width(False)
        self.update_preview()
        self.set_advanced_editor_visible(False)
        self.update_post_actions(None)

    def _page_heading(self, title: str, description: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        detail = QLabel(description)
        detail.setObjectName("mutedText")
        layout.addWidget(heading)
        layout.addWidget(detail)
        return layout

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(18)
        top = QHBoxLayout()
        top.addLayout(self._page_heading("오늘 무엇을 할까요?", "검토할 글과 게시 상태를 한눈에 확인하세요."))
        top.addStretch()
        self.dashboard_category = QComboBox()
        self.dashboard_category.addItem("전체 카테고리에서 찾기", None)
        for category in CATEGORIES:
            self.dashboard_category.addItem(category, category)
        top.addWidget(self.dashboard_category)
        create_button = QPushButton("+ 새 글 만들기")
        create_button.clicked.connect(self.generate_from_dashboard)
        top.addWidget(create_button)
        layout.addLayout(top)
        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.dashboard_counts = {}
        for key, label in (("draft", "검토할 글"), ("failed", "게시 실패"), ("published", "게시 완료"), ("views", "누적 조회수")):
            card = QFrame()
            card.setObjectName("summaryCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 18, 20, 18)
            card_layout.setSpacing(6)
            caption = QLabel(label)
            caption.setObjectName("summaryCaption")
            value = QLabel("0")
            value.setObjectName("summaryNumber")
            card_layout.addWidget(caption)
            card_layout.addWidget(value)
            cards.addWidget(card)
            self.dashboard_counts[key] = value
        layout.addLayout(cards)
        guide = QFrame()
        guide.setObjectName("summaryCard")
        guide_layout = QVBoxLayout(guide)
        guide_layout.setContentsMargins(20, 18, 20, 18)
        guide_layout.setSpacing(10)
        guide_layout.addWidget(QLabel("<b>처음이라면 이렇게 시작해보세요</b>"))
        guide_layout.addWidget(QLabel("새 글 만들기  →  내용 확인  →  티스토리에 게시"))
        failed_button = QPushButton("실패한 게시글 확인")
        failed_button.setProperty("secondary", True)
        failed_button.setMaximumWidth(190)
        failed_button.clicked.connect(lambda: self.open_post_list("실패"))
        guide_layout.addWidget(failed_button)
        layout.addWidget(guide)
        layout.addStretch()
        return page

    def _build_channels_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(14)
        layout.addLayout(self._page_heading("채널 연결", "게시할 서비스를 하나씩 연결해두세요."))
        for name, state, enabled, handler in (
            ("티스토리", "Chrome 로그인 세션 사용", True, self.login),
            ("네이버 블로그", "연결 기능 준비 중", False, None),
            ("인스타그램", "연결 기능 준비 중", False, None),
        ):
            row = QFrame()
            row.setObjectName("summaryCard")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(20, 17, 20, 17)
            text = QLabel(f"<b>{name}</b><br><span style='color:#718078'>{state}</span>")
            button = QPushButton("연결 확인" if enabled else "준비 중")
            button.setProperty("secondary", True)
            button.setEnabled(enabled)
            if handler:
                button.clicked.connect(handler)
            row_layout.addWidget(text, 1)
            row_layout.addWidget(button)
            layout.addWidget(row)
        notice = QLabel("비밀번호는 앱 데이터베이스에 저장하지 않습니다. 각 서비스의 안전한 로그인 세션을 사용합니다.")
        notice.setWordWrap(True)
        notice.setObjectName("mutedText")
        notice.setStyleSheet("padding:10px")
        layout.addWidget(notice)
        layout.addStretch()
        return page

    def _build_tistory_posts_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(14)
        top = QHBoxLayout()
        top.addLayout(self._page_heading("게시된 글", "티스토리에 올라간 글을 최신순으로 확인하세요."))
        top.addStretch()
        self.tistory_refresh_button = QPushButton("목록 새로고침")
        self.tistory_refresh_button.setProperty("secondary", True)
        self.tistory_refresh_button.clicked.connect(self.refresh_tistory_posts)
        top.addWidget(self.tistory_refresh_button)
        layout.addLayout(top)
        self.tistory_sync_status = QLabel("목록을 열면 최신 게시글부터 티스토리 정보를 가져옵니다.")
        self.tistory_sync_status.setObjectName("mutedText")
        self.tistory_sync_status.setStyleSheet("padding:4px 0")
        layout.addWidget(self.tistory_sync_status)
        self.tistory_table = QTableWidget(0, 6)
        self.tistory_table.setHorizontalHeaderLabels(["순번", "제목", "상태", "카테고리", "조회수", "관리"])
        self.tistory_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tistory_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tistory_table.setAlternatingRowColors(True)
        self.tistory_table.verticalHeader().setVisible(False)
        self.tistory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tistory_table.setColumnWidth(0, 75)
        self.tistory_table.setColumnWidth(2, 75)
        self.tistory_table.setColumnWidth(3, 110)
        self.tistory_table.setColumnWidth(4, 75)
        self.tistory_table.setColumnWidth(5, 210)
        layout.addWidget(self.tistory_table, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(14)
        layout.addLayout(self._page_heading("설정", "수집 범위와 게시 방식을 편하게 확인하세요."))
        policy = QFrame()
        policy.setObjectName("summaryCard")
        policy_layout = QVBoxLayout(policy)
        policy_layout.setContentsMargins(22, 20, 22, 20)
        policy_layout.setSpacing(10)
        policy_layout.addWidget(QLabel("<b>어디에서 글을 가져오나요?</b>"))
        policy_layout.addWidget(QLabel("전국 공식 행사 · 수도권 약 70% / 비수도권 약 30%"))
        policy_layout.addWidget(QLabel("<b>글은 어떻게 게시되나요?</b>"))
        policy_layout.addWidget(QLabel("자동 게시는 꺼져 있으며, 필요한 글만 직접 게시합니다."))
        layout.addWidget(policy)
        layout.addStretch()
        return page

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for button in self.nav_buttons:
            button.setProperty("active", False)
            button.style().unpolish(button)
            button.style().polish(button)
        active_index = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}.get(index)
        if active_index is not None:
            button = self.nav_buttons[active_index]
            button.setProperty("active", True)
            button.style().unpolish(button)
            button.style().polish(button)

    def open_create_page(self) -> None:
        choices = ["전체 카테고리", *CATEGORIES]
        selected, accepted = QInputDialog.getItem(
            self,
            "새 글 만들기",
            "어떤 종류의 글을 만들까요?",
            choices,
            0,
            False,
        )
        if not accepted:
            return
        self.generation_category.setCurrentIndex(choices.index(selected))
        self.show_page(1)
        self.nav_buttons[1].setProperty("active", True)
        self.nav_buttons[1].style().unpolish(self.nav_buttons[1])
        self.nav_buttons[1].style().polish(self.nav_buttons[1])
        self.content_title.setText("새 글 만들기")
        self.content_description.setText("공식 자료를 찾아 초안을 만들어요. 완성된 글은 바로 옆에서 확인할 수 있습니다.")
        self.generate_post()

    def open_post_list(self, status: str) -> None:
        self.show_page(1)
        self.content_title.setText("글 관리")
        self.content_description.setText("글을 골라 내용을 확인하고, 필요한 작업만 진행하세요.")
        self.status_filter.setCurrentText(status)
        self.refresh_tistory_posts(show_errors=False)

    def show_tistory_posts(self) -> None:
        self.show_page(2)
        self.refresh_tistory_posts()

    def refresh_tistory_posts(self, *, show_errors: bool = True) -> None:
        if self.tistory_posts_worker and self.tistory_posts_worker.isRunning():
            return
        self.show_tistory_sync_errors = show_errors
        self.tistory_refresh_button.setEnabled(False)
        self.tistory_sync_status.setText("티스토리에서 실제 게시글 목록을 가져오는 중…")
        self.tistory_posts_worker = TistoryPostsWorker(self.service)
        self.tistory_posts_worker.succeeded.connect(self.tistory_posts_loaded)
        self.tistory_posts_worker.failed.connect(self.tistory_posts_failed)
        self.tistory_posts_worker.start()

    def tistory_posts_loaded(self, posts: list[dict]) -> None:
        self.remote_posts = posts
        self.tistory_refresh_button.setEnabled(True)
        self.tistory_table.setRowCount(len(posts))
        for row, post in enumerate(posts):
            views = post.get("views")
            values = (row + 1, post["title"], post["visibility"], post["category"], f"{views:,}" if isinstance(views, int) else "—")
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.UserRole, int(post["id"]))
                    item.setTextAlignment(Qt.AlignCenter)
                if column == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                self.tistory_table.setItem(row, column, item)
            self.tistory_table.setRowHeight(row, 48)
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(0, 0, 0, 0)
            edit_button = QPushButton("수정")
            edit_button.setProperty("secondary", True)
            edit_button.setMinimumWidth(72)
            edit_button.clicked.connect(lambda _checked=False, post_id=post["id"]: self.open_tistory_editor(post_id))
            delete_button = QPushButton("삭제")
            delete_button.setProperty("secondary", True)
            delete_button.setMinimumWidth(72)
            delete_button.clicked.connect(
                lambda _checked=False, post_id=post["id"], title=post["title"]: self.confirm_tistory_delete(post_id, title)
            )
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            self.tistory_table.setCellWidget(row, 5, actions)
        self.tistory_sync_status.setText(f"티스토리 실제 게시글 {len(posts)}개 · 방금 동기화")
        self.refresh_posts()

    def tistory_posts_failed(self, message: str) -> None:
        self.tistory_refresh_button.setEnabled(True)
        self.tistory_sync_status.setText("티스토리 목록을 가져오지 못했습니다.")
        if getattr(self, "show_tistory_sync_errors", True):
            QMessageBox.warning(self, "티스토리 동기화 실패", message)

    def open_tistory_editor(self, post_id: int) -> None:
        process = QProcess(self)
        bundled_python = RUNTIME_ROOT / ".python" / "python.exe"
        program = str(bundled_python) if bundled_python.is_file() else sys.executable
        process.setWorkingDirectory(str(RUNTIME_ROOT))
        process.start(program, ["-m", "active_log.main", "edit-post", str(post_id)])
        self.login_process = process
        self.statusBar().showMessage(f"티스토리 글 {post_id} 수정 창을 열었습니다.", 5000)

    def confirm_tistory_delete(self, post_id: int, title: str) -> None:
        if QMessageBox.warning(
            self,
            "티스토리에서 실제 삭제",
            f"'{title}'을 티스토리에서 실제로 삭제할까요?\n\n삭제한 글은 복구하기 어렵습니다.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        ) != QMessageBox.Yes:
            return
        confirm_text, accepted = QInputDialog.getText(
            self, "삭제 확인", "실제 삭제를 진행하려면 '삭제'를 입력하세요."
        )
        if not accepted or confirm_text.strip() != "삭제":
            return
        self.tistory_refresh_button.setEnabled(False)
        self.tistory_sync_status.setText(f"티스토리 글 {post_id} 삭제 결과를 확인하는 중…")
        self.tistory_delete_worker = TistoryDeleteWorker(self.service, post_id)
        self.tistory_delete_worker.succeeded.connect(self.tistory_delete_succeeded)
        self.tistory_delete_worker.failed.connect(self.tistory_delete_failed)
        self.tistory_delete_worker.start()

    def tistory_delete_succeeded(self, post_id: int) -> None:
        QMessageBox.information(self, "삭제 완료", f"티스토리 글 {post_id}을 삭제했습니다.")
        self.refresh_tistory_posts()

    def tistory_delete_failed(self, message: str) -> None:
        self.tistory_refresh_button.setEnabled(True)
        self.tistory_sync_status.setText("티스토리 삭제를 완료하지 못했습니다.")
        QMessageBox.critical(self, "티스토리 삭제 실패", message)

    def generate_from_dashboard(self) -> None:
        self.generation_category.setCurrentIndex(self.dashboard_category.currentIndex())
        self.show_page(1)
        self.generate_post()

    def set_advanced_editor_visible(self, visible: bool) -> None:
        for widget in self.advanced_widgets:
            widget.setVisible(visible)
        self.advanced_button.setText("고급 옵션 닫기" if visible else "고급 옵션")
        post = self.db.get_post(self.current_id) if self.current_id else None
        self.delete_button.setVisible(visible and bool(post))

    def toggle_advanced_editor(self) -> None:
        self.set_advanced_editor_visible(not self.body.isVisible())

    def toggle_editor_panel(self) -> None:
        if self.current_remote_post:
            self.open_tistory_editor(int(self.current_remote_post["id"]))
            return
        visible = not self.editor_panel.isVisible()
        self.editor_panel.setVisible(visible)
        self.edit_toggle_button.setText("수정 닫기" if visible else "내용 수정")
        self.content_splitter.setSizes([380, 390 if visible else 0, 720 if visible else 1110])

    def perform_preview_action(self) -> None:
        if self.current_remote_post:
            QDesktopServices.openUrl(QUrl(self.current_remote_post["url"]))
            return
        post = self.db.get_post(self.current_id) if self.current_id else None
        status = post.get("status") if post else None
        if status == "draft":
            self.publish()
        elif status == "failed":
            self.retry_failed_publish()
        elif status in {"private", "public"}:
            self.open_published()

    def refresh_posts(self, select_id: int | None = None) -> None:
        oldest_first = bool(self.order_filter.currentData()) if hasattr(self, "order_filter") else False
        all_local_rows = self.db.list_posts(200, oldest_first=oldest_first)
        local_rows = (
            [post for post in all_local_rows if post["status"] in {"draft", "failed", "publishing"}]
            if self.remote_posts else all_local_rows
        )
        display_rows = [("local", post) for post in local_rows]
        display_rows.extend(("tistory", post) for post in self.remote_posts)
        self.table.blockSignals(True)
        self.table.setRowCount(len(display_rows))
        selected_row = None
        for row_index, (source, post) in enumerate(display_rows):
            status_labels = {
                "draft": "대기", "publishing": "게시 중",
                "private": "비공개", "public": "완료", "failed": "실패",
            }
            if source == "tistory":
                raw_visibility = str(post.get("visibility", ""))
                normalized_status = "private" if "비공개" in raw_visibility else "public"
                status_text = "티스토리 비공개" if normalized_status == "private" else "티스토리"
            else:
                normalized_status = post["status"]
                status_text = status_labels.get(normalized_status, normalized_status)
            views = post.get("views") if source == "tistory" else None
            values = (
                row_index + 1, post["title"], status_text,
                f"{views:,}" if isinstance(views, int) else "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.UserRole, {"source": source, "id": int(post["id"])})
                if column == 1:
                    item.setData(Qt.UserRole, post["category"])
                if column == 2:
                    colors = {"draft": "#347b56", "publishing": "#a87324", "private": "#5076a7", "public": "#7664a7", "failed": "#c04f44"}
                    item.setData(Qt.UserRole, normalized_status)
                    item.setForeground(QColor(colors.get(normalized_status, "#4b5650")))
                if column in {0, 3}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_index, column, item)
            if source == "local" and select_id == post["id"]:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row is not None:
            self.table.selectRow(selected_row)
        self.apply_filters()
        if hasattr(self, "dashboard_counts"):
            counts = {
                "draft": sum(post["status"] == "draft" for post in all_local_rows),
                "failed": sum(post["status"] == "failed" for post in all_local_rows),
                "published": len(self.remote_posts) or sum(post["status"] in {"private", "public"} for post in all_local_rows),
                "views": sum(int(post.get("views") or 0) for post in self.remote_posts),
            }
            for key, value in counts.items():
                self.dashboard_counts[key].setText(str(value))
        self.statusBar().showMessage(
            f"글 {len(display_rows)}개 · 대기 {self.db.count_drafts()}개 · 티스토리 {len(self.remote_posts)}개"
        )

    def load_selected(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        id_item = self.table.item(items[0].row(), 0)
        target = id_item.data(Qt.UserRole)
        target_is_current_local = (
            isinstance(target, dict)
            and target.get("source") == "local"
            and self.current_id == int(target["id"])
        )
        if self.dirty and self.current_id is not None and not target_is_current_local:
            answer = QMessageBox.question(self, "저장하지 않은 변경", "변경사항을 저장하고 다른 글을 열까요?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel:
                self.refresh_posts(self.current_id)
                return
            if answer == QMessageBox.Save and not self.save_post():
                self.refresh_posts(self.current_id)
                return
        if isinstance(target, dict) and target.get("source") == "tistory":
            remote = next(
                (post for post in self.remote_posts if int(post["id"]) == int(target["id"])), None
            )
            if remote:
                self.dirty = False
                self.current_id = None
                self.current_remote_post = remote
                self.editor_panel.hide()
                self.edit_toggle_button.setText("티스토리에서 수정")
                self.edit_toggle_button.setEnabled(True)
                self.preview_primary_button.setText("티스토리에서 보기")
                self.preview_primary_button.setEnabled(True)
                self.preview.load(QUrl(remote["url"]))
                self.post_detail.setText("티스토리에 실제 게시된 글입니다.")
            return
        selected_id = int(target["id"] if isinstance(target, dict) else target)
        post = self.db.get_post(selected_id)
        if not post:
            return
        self.loading = True
        self.current_remote_post = None
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
            if self.current_id is not None:
                self.save_button.setVisible(True)
            self.statusBar().showMessage("저장하지 않은 변경사항이 있습니다.")

    def apply_filters(self) -> None:
        query = self.search.text().strip().lower() if hasattr(self, "search") else ""
        labels = {"검토 대기": "draft", "게시 중": "publishing", "공개 게시": "public", "실패": "failed"}
        status = labels.get(self.status_filter.currentText(), "") if hasattr(self, "status_filter") else ""
        for row in range(self.table.rowCount()):
            title_item = self.table.item(row, 1)
            haystack = f"{title_item.text()} {title_item.data(Qt.UserRole) or ''}".lower()
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
        self.republish_button.setVisible(False)
        self.save_button.setVisible(bool(post) and self.dirty and status in {"draft", "failed"})
        self.advanced_button.setVisible(status not in {"publishing"})
        self.delete_button.setVisible(self.body.isVisible() and bool(post) and status != "publishing")
        self.delete_button.setEnabled(bool(post) and status != "publishing")
        self.publish_button.setEnabled(status == "draft")
        self.publish_button.setVisible(status == "draft")
        self.publish_button.setText(
            "티스토리에 공개 게시" if status == "draft" else ""
        )
        preview_labels = {
            "draft": "티스토리에 게시",
            "failed": "게시 다시 시도",
            "private": "티스토리에서 보기",
            "public": "티스토리에서 보기",
            "publishing": "게시 중…",
        }
        self.preview_primary_button.setText(preview_labels.get(status, "글을 선택하세요"))
        self.preview_primary_button.setEnabled(status in {"draft", "failed", "private", "public"})
        self.edit_toggle_button.setEnabled(bool(post) and status != "publishing")
        if not post:
            self.post_detail.setText("새 글을 작성 중입니다.")
        elif status == "failed":
            self.post_detail.setText(f"게시 실패 · {post.get('error') or '오류 정보 없음'}")
            self.post_detail.setStyleSheet("color:#c04f44;padding:6px 2px")
        else:
            status_label = {"draft": "검토 대기", "publishing": "게시 중", "private": "비공개 게시 완료", "public": "공개 게시 완료", "failed": "게시 실패"}.get(status, status)
            self.post_detail.setText(f"상태: {status_label}" + (f" · {post.get('tistory_url')}" if post.get("tistory_url") else ""))
            self.post_detail.setStyleSheet("color:#718078;padding:6px 2px")

    def requeue_current(self) -> None:
        if self.current_id is None:
            return
        self.db.requeue_post(self.current_id)
        self.refresh_posts(self.current_id)
        self.statusBar().showMessage("게시 대기 상태로 변경했습니다.", 5000)

    def retry_failed_publish(self) -> None:
        if self.current_id is None:
            return
        post = self.db.get_post(self.current_id)
        if not post or post.get("status") != "failed":
            return
        if self.dirty and not self.save_post():
            return
        if not self.show_quality_report():
            return
        self.db.requeue_post(self.current_id)
        self.refresh_posts(self.current_id)
        self._start_publish()

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
        category = self.generation_category.currentData()
        self.generation_worker = GenerateWorker(self.service, category)
        self.generation_worker.succeeded.connect(self.generation_succeeded)
        self.generation_worker.failed.connect(self.generation_failed)
        self.generate_action.setEnabled(False)
        self.generation_category.setEnabled(False)
        self.generation_worker.start()
        target = category or "전체 카테고리"
        self.statusBar().showMessage(f"{target} 공식 정보와 포스터를 수집하는 중…")

    def generation_succeeded(self, post_id: int) -> None:
        self.generate_action.setEnabled(True)
        self.generation_category.setEnabled(True)
        self.refresh_posts(post_id)
        self.statusBar().showMessage("새 게시글을 생성해 검토 대기 상태로 저장했습니다.", 8000)

    def generation_failed(self, message: str) -> None:
        self.generate_action.setEnabled(True)
        self.generation_category.setEnabled(True)
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
            self.preview.setZoomFactor(1.0)
            self.preview.setMinimumWidth(390)
            self.preview.setMaximumWidth(390)
        else:
            self.preview.setZoomFactor(0.62)
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
        if self.tistory_posts_worker and self.tistory_posts_worker.isRunning():
            QMessageBox.information(self, "티스토리 동기화 중", "게시글 목록 확인이 끝날 때까지 기다려 주세요.")
            event.ignore()
            return
        if self.tistory_delete_worker and self.tistory_delete_worker.isRunning():
            QMessageBox.information(self, "티스토리 삭제 확인 중", "삭제 결과 확인이 끝날 때까지 기다려 주세요.")
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
