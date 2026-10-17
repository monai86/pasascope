"""In English the window shows no Thai interface text (only the children's own data may be Thai)."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

pytest.importorskip("PySide6")

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = textwrap.dedent('''
    import re, sys
    from datetime import date
    from pathlib import Path
    sys.path[:0] = [".", "apps/api"]
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget, QTableWidget, QListWidget, QTextBrowser, QComboBox, QCheckBox
    app = QApplication([])
    from packages.desktop.core import DesktopService, open_workspace
    from packages.desktop.core.i18n import set_language
    service = DesktopService(open_workspace(Path(sys.argv[1])))
    set_language("en")
    from packages.desktop.ui.main_window import MainWindow
    service.set_therapist_name("Test Therapist")
    case = service.create_case("EN-001", 50, nickname="Sam")
    service.grant_consent(case.case_id, "Parent", date(2026, 10, 1))
    session = service.create_session(case.case_id, date(2026, 10, 2))
    chat = "@Begin\\n@Languages:\\teng\\n@Participants:\\tCHI Target_Child, INV Investigator\\n*INV:\\twhat is that ?\\n*CHI:\\ta red car .\\n*INV:\\ta red car .\\n*CHI:\\tcar go fast .\\n@End\\n"
    transcript = service.import_transcript_text(session.session_id, chat)
    service.create_case("EN-002", 40)
    window = MainWindow(service)
    thai = re.compile("[\\u0e00-\\u0e7f]")
    found = []
    def pump():
        for _ in range(4): app.processEvents()
    def collect(where):
        pump()
        texts = []
        for widget in window.findChildren(QLabel) + window.findChildren(QPushButton) + window.findChildren(QCheckBox):
            if widget.isVisible(): texts += [widget.text(), widget.toolTip()]
        for tabs in window.findChildren(QTabWidget):
            texts += [tabs.tabText(i) for i in range(tabs.count())]
        for table in window.findChildren(QTableWidget):
            if table.isVisible():
                texts += [table.horizontalHeaderItem(i).text() for i in range(table.columnCount()) if table.horizontalHeaderItem(i)]
        for combo in window.findChildren(QComboBox):
            if combo.isVisible(): texts += [combo.itemText(i) for i in range(combo.count())]
        for browser in window.findChildren(QTextBrowser):
            if browser.isVisible(): texts.append(browser.toPlainText())
        for menu_action in window.menuBar().actions():
            texts.append(menu_action.text())
            if menu_action.menu():
                for action in menu_action.menu().actions():
                    texts.append(action.text())
                    if action.menu(): texts += [a.text() for a in action.menu().actions()]
        for text in texts:
            # the language menu is bilingual on purpose, so a Thai reader can find it
            if thai.search(text or "") and text not in ("ไทย", "Language / ภาษา"):
                found.append((where, text[:80]))
    collect("home")
    window.show_knowledge()
    for row in range(window.knowledge.topics.count()):
        window.knowledge.topics.setCurrentRow(row); collect(f"knowledge {row}")
    window.reload_cases(case.case_id); window.open_case(case.case_id, session.session_id)
    for tab in range(4):
        window.tabs.setCurrentIndex(tab); collect(f"tab {tab}")
    service.attest(transcript.transcript_id, override_reason="checked")
    service.analyze(session.session_id)
    window.refresh_session()
    for tab in range(4):
        window.tabs.setCurrentIndex(tab); collect(f"analysed tab {tab}")
    window.reload_cases(); window.show_home(); collect("home again")
    for where, text in found: print(where, "|", text)
    print("THAI_FOUND", len(found))
''')


def test_english_interface_has_no_thai_text(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PASASCOPE_LANGUAGE="en")
    result = subprocess.run([sys.executable, "-c", SCRIPT, str(tmp_path / "ws")], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=240)
    assert "THAI_FOUND" in result.stdout, result.stderr[-3000:]
    assert "THAI_FOUND 0" in result.stdout, result.stdout[-3000:]
