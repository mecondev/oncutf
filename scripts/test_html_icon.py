
"""
Module: .cache/test_html_icon.py

Author: Michael Economou
Date: 2025-06-14

This module provides functionality for the OnCutF batch file renaming application.
"""

from PyQt5.QtWidgets import QApplication, QTextEdit

from utils.icon_utilities import create_colored_html_icon

app = QApplication([])

# Creating rich text with inline indicators
html = (
    "<p>Status Summary:</p>"
    f"{create_colored_html_icon('#2ecc71')} Valid<br>"
    f"{create_colored_html_icon('#777777')} Unchanged<br>"
    f"{create_colored_html_icon('#c0392b')} Invalid<br>"
    f"{create_colored_html_icon('#e67e22')} Duplicate"
)

text_edit = QTextEdit()
text_edit.setReadOnly(True)
text_edit.setHtml(html)
text_edit.setMinimumSize(300, 150)
text_edit.show()

app.exec_()
