"""The first start on a new data folder: what PasaScope is, what to know, and who signs.

Shown once, when the data folder has no therapist name yet (a new computer
or a new data folder). An update or a reinstall keeps the data folder, its
name and its cases, so it does not come back. Laid out like an editor's
walkthrough: steps on the left, the step on the right, Back and Next below.
Choosing a language redraws the steps in it at once; the window that opens
afterwards is built in that language.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core.i18n import language, set_language, tr
from packages.desktop.ui import motion

LOGO = Path(__file__).resolve().parent / "assets" / "logo.png"


def default_language() -> str:
    """Thai on a computer set to Thai, English otherwise."""
    return "th" if QLocale.system().language() == QLocale.Language.Thai else "en"


def _label(text: str, name: str = "", wrap: bool = True) -> QLabel:
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def _button(text: str, role: str = "") -> QPushButton:
    widget = QPushButton(text)
    if role:
        widget.setProperty("role", role)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Onboarding(QDialog):
    STEPS = 3

    def __init__(self, service, data_folder: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.data_folder = data_folder
        self.step = 0
        self.code = language()
        self.name_text = service.therapist_name
        self.clinic_text = service.organization
        self.understood = False
        self.model_installed = bool(service.thai_model_status().get("installed"))
        self.model_size_gb = service.thai_model_status().get("size", 0) / 1_000_000_000
        self.download_models = not self.model_installed
        self.setObjectName("Onboarding")
        self.setModal(True)
        self.setFixedSize(820, 560)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.side = QFrame()
        self.side.setObjectName("OnboardingSide")
        self.side.setFixedWidth(250)
        root.addWidget(self.side)
        main = QWidget()
        root.addWidget(main, 1)
        self.main_layout = QVBoxLayout(main)
        self.main_layout.setContentsMargins(36, 30, 36, 22)
        self.main_layout.setSpacing(0)
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages, 1)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.back_btn = _button("")
        self.back_btn.clicked.connect(lambda: self._go(self.step - 1))
        self.next_btn = _button("", "primary")
        self.next_btn.setDefault(True)
        self.next_btn.clicked.connect(self._next)
        self.hint = _label("", "Hint")
        buttons.addWidget(self.hint, 1)
        buttons.addWidget(self.back_btn)
        buttons.addWidget(self.next_btn)
        self.main_layout.addLayout(buttons)
        self._build()

    # ------------------------------------------------------------------
    # Building, and rebuilding when the language changes
    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.setWindowTitle(tr("ยินดีต้อนรับสู่ PasaScope", "Welcome to PasaScope"))
        self._build_side()
        while self.pages.count():
            page = self.pages.widget(0)
            self.pages.removeWidget(page)
            page.deleteLater()
        for page in (self._welcome_page(), self._notes_page(), self._details_page()):
            self.pages.addWidget(page)
        self._go(self.step, animate=False)

    def _build_side(self) -> None:
        old = self.side.layout()
        if old is not None:
            QWidget().setLayout(old)  # drop the old layout and its widgets
        layout = QVBoxLayout(self.side)
        layout.setContentsMargins(22, 26, 18, 20)
        layout.setSpacing(6)
        brand = QHBoxLayout()
        mark = QLabel()
        logo = QPixmap(str(LOGO))
        if not logo.isNull():
            ratio = self.devicePixelRatioF() or 1.0
            logo = logo.scaled(int(30 * ratio), int(30 * ratio), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            logo.setDevicePixelRatio(ratio)
            mark.setPixmap(logo)
        brand.addWidget(mark)
        brand.addWidget(_label("PasaScope", "Brand", wrap=False))
        brand.addStretch(1)
        layout.addLayout(brand)
        layout.addSpacing(22)
        layout.addWidget(_label(tr("เริ่มต้นใช้งาน", "GET STARTED"), "SidebarHeading"))
        layout.addSpacing(4)
        self.step_items = []
        for index, title in enumerate(self._step_titles()):
            item = _label(f"{index + 1}   {title}", "StepItem", wrap=False)
            self.step_items.append(item)
            layout.addWidget(item)
        layout.addStretch(1)
        layout.addWidget(_label(tr("ตั้งค่าเหล่านี้เปลี่ยนภายหลังได้ในเมนู ตั้งค่า", "You can change these later in Settings."), "Hint"))

    def _step_titles(self) -> list[str]:
        return [tr("ยินดีต้อนรับ", "Welcome"), tr("ก่อนเริ่มใช้งาน", "Before you start"), tr("ข้อมูลของคุณ", "Your details")]

    def _welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(_label(tr("ยินดีต้อนรับสู่ PasaScope", "Welcome to PasaScope"), "WelcomeTitle"), 1)
        for code, name in (("th", "ไทย"), ("en", "English")):
            choice = _button(name, "segment")
            choice.setCheckable(True)
            choice.setChecked(code == self.code)
            choice.clicked.connect(lambda _=False, c=code: self._set_language(c))
            top.addWidget(choice, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)
        layout.addWidget(_label(tr(
            "PasaScope ช่วยนักบำบัดถอดเสียงตัวอย่างภาษาของเด็ก ตรวจ transcript คำนวณตัวชี้วัดทางภาษา และทำรายงาน ทั้งหมดบนเครื่องนี้",
            "PasaScope helps therapists transcribe a child's language sample, check the transcript, measure it and write the report, all on this computer.",
        ), "Muted"))
        layout.addSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(12)
        tiles = [
            (tr("1  เสียง", "1  Recording"), tr("บันทึกจากไมโครโฟน หรือนำเข้าไฟล์เสียงหรือ transcript", "Record from the microphone, or import audio or a transcript.")),
            (tr("2  Transcript", "2  Transcript"), tr("ฟังทีละบรรทัด แก้ข้อความและผู้พูด แล้วรับรอง", "Listen line by line, fix the words and speakers, then attest.")),
            (tr("3  ตัวชี้วัด", "3  Findings"), tr("MLU, NDW, การผลัดกันพูด และ cue ที่ควรดูซ้ำ", "MLU, NDW, turn-taking, and cues worth a second look.")),
            (tr("4  รายงาน", "4  Report"), tr("รายงาน A4 ภาษาไทยหรืออังกฤษ ลงนามแล้ว export เป็น PDF", "An A4 report in Thai or English, signed and exported as PDF.")),
        ]
        for index, (title, body) in enumerate(tiles):
            tile = QFrame()
            tile.setObjectName("FeatureTile")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(14, 12, 14, 12)
            tile_layout.setSpacing(4)
            tile_layout.addWidget(_label(title, "SectionTitle", wrap=False))
            tile_layout.addWidget(_label(body, "Hint"))
            grid.addWidget(tile, index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
        return page

    def _notes_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(_label(tr("ก่อนเริ่มใช้งาน", "Before you start"), "WelcomeTitle"))
        notes = [
            (tr("ไม่ใช่เครื่องมือวินิจฉัย", "Not a diagnostic tool"),
             tr("ผลเป็นข้อมูลประกอบการตัดสินใจของนักบำบัด และยังไม่ได้ตรวจสอบความถูกต้องทางคลินิกกับเด็กไทย",
                "Results support the therapist's judgement. They have not been clinically validated with Thai children.")),
            (tr("ข้อมูลอยู่ในเครื่องนี้", "Your data stays on this computer"),
             tr(f"เคส เสียง และรายงานเก็บที่ {self.data_folder} แยกจากตัวโปรแกรม อัปเดตหรือติดตั้งใหม่แล้วข้อมูลยังอยู่ครบ",
                f"Cases, recordings and reports are kept in {self.data_folder}, apart from the app. Updating or reinstalling keeps them.")),
            (tr("ต้องมีความยินยอมก่อน", "Consent comes first"),
             tr("บันทึกความยินยอมของผู้ปกครองก่อนบันทึกเสียงหรือเพิ่มข้อมูลของเด็ก", "Record the parent's or guardian's consent before adding recordings or other data.")),
            (tr("สำรองข้อมูลสม่ำเสมอ", "Back up regularly"),
             tr("ไฟล์สำรองไม่เข้ารหัส เก็บไว้ในที่ที่มีแต่นักบำบัดเข้าถึงได้", "Backups are not encrypted; keep them where only therapists can reach them.")),
        ]
        for title, body in notes:
            item = QFrame()
            item.setObjectName("NoteItem")
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(14, 8, 0, 8)
            item_layout.setSpacing(2)
            item_layout.addWidget(_label(title, "SectionTitle"))
            item_layout.addWidget(_label(body, "Hint"))
            layout.addWidget(item)
        layout.addStretch(1)
        self.understood_box = QCheckBox(tr("ฉันเข้าใจข้อจำกัดเหล่านี้", "I understand these limits"))
        self.understood_box.setChecked(self.understood)
        self.understood_box.toggled.connect(self._on_understood)
        layout.addWidget(self.understood_box)
        return page

    def _details_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(_label(tr("ข้อมูลของคุณ", "Your details"), "WelcomeTitle"))
        layout.addWidget(_label(tr(
            "ชื่อนี้อยู่ในการรับรอง transcript การตรวจ cue และการลงนามรายงาน",
            "Your name appears on transcript attestations, cue reviews and signed reports.",
        ), "Muted"))
        layout.addSpacing(10)
        layout.addWidget(_label(tr("ชื่อนักบำบัด", "Therapist name"), "SectionTitle", wrap=False))
        self.name = QLineEdit(self.name_text)
        self.name.setMaxLength(120)
        self.name.setPlaceholderText(tr("เช่น นางสาวกานดา ใจดี (นักแก้ไขการพูด)", "For example Kanda Jaidee, speech-language pathologist"))
        self.name.textChanged.connect(self._on_name)
        layout.addWidget(self.name)
        layout.addSpacing(8)
        layout.addWidget(_label(tr("ชื่อหน่วยงาน (ไม่บังคับ)", "Clinic name (optional)"), "SectionTitle", wrap=False))
        self.clinic = QLineEdit(self.clinic_text)
        self.clinic.setMaxLength(120)
        self.clinic.setPlaceholderText(tr("พิมพ์ที่หัวกระดาษของรายงาน", "Printed at the top of each report page"))
        self.clinic.textChanged.connect(lambda text: setattr(self, "clinic_text", text))
        layout.addWidget(self.clinic)
        layout.addSpacing(14)
        if self.model_installed:
            layout.addWidget(_label(tr("โมเดลถอดเสียงภาษาไทยอยู่ในเครื่องแล้ว", "The Thai speech model is already on this computer."), "Hint"))
        else:
            self.models_box = QCheckBox(tr(
                f"ดาวน์โหลดโมเดลถอดเสียงภาษาไทย (ประมาณ {self.model_size_gb:.1f} GB ครั้งเดียว) หลังเปิดโปรแกรม",
                f"Download the Thai speech model (about {self.model_size_gb:.1f} GB, once) after opening",
            ))
            self.models_box.setChecked(self.download_models)
            self.models_box.toggled.connect(lambda on: setattr(self, "download_models", on))
            layout.addWidget(self.models_box)
            layout.addWidget(_label(tr("ทำภายหลังได้ที่ ตั้งค่า → ดาวน์โหลดโมเดลถอดเสียง", "You can do it later in Settings → Download speech models."), "Hint"))
        layout.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------
    def _go(self, step: int, animate: bool = True) -> None:
        self.step = max(0, min(self.STEPS - 1, step))
        self.pages.setCurrentIndex(self.step)
        for index, item in enumerate(self.step_items):
            item.setProperty("state", "done" if index < self.step else "current" if index == self.step else "todo")
            _repolish(item)
        self.back_btn.setText(tr("ย้อนกลับ", "Back"))
        self.back_btn.setVisible(self.step > 0)
        last = self.step == self.STEPS - 1
        self.next_btn.setText(tr("เริ่มใช้งาน", "Start using PasaScope") if last else tr("ถัดไป", "Next"))
        self._update_next()
        if animate:
            motion.fade_in(self.pages.currentWidget())
        if last:
            self.name.setFocus()

    def _update_next(self) -> None:
        if self.step == 1:
            ready, hint = self.understood, tr("ติ๊กช่องด้านล่างเพื่อไปต่อ", "Tick the box below to go on.")
        elif self.step == 2:
            ready, hint = bool(self.name_text.strip()), tr("ใส่ชื่อนักบำบัดเพื่อเริ่มใช้งาน", "Enter the therapist name to start.")
        else:
            ready, hint = True, ""
        self.next_btn.setEnabled(ready)
        self.hint.setText("" if ready else hint)

    def _on_understood(self, on: bool) -> None:
        self.understood = on
        self._update_next()

    def _on_name(self, text: str) -> None:
        self.name_text = text
        self._update_next()

    def _set_language(self, code: str) -> None:
        if code != self.code:
            self.code = code
            set_language(code)
            self._build()
        else:
            self._build()  # keep the pressed segment checked

    def _next(self) -> None:
        if self.step < self.STEPS - 1:
            self._go(self.step + 1)
            return
        try:
            self.service.set_language(self.code)
            self.service.set_therapist_name(self.name_text)
            if self.clinic_text.strip() != self.service.organization:
                self.service.set_organization(self.clinic_text)
        except Exception as exc:  # noqa: BLE001 - shown where the button is
            self.hint.setText(str(exc))
            return
        self.accept()


def run_onboarding(service, data_folder: Path) -> Onboarding | None:
    """Ask for the first-start details; None when the therapist closed the window instead."""
    code = default_language() if not service.workspace.read_profile().get("language") else service.language
    set_language(code)
    dialog = Onboarding(service, data_folder)
    return dialog if dialog.exec() == QDialog.DialogCode.Accepted else None
