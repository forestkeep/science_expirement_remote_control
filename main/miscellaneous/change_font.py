from PyQt5 import Qt

class MainWindow(Qt.QMainWindow):
    def __init__(self):
        super().__init__()

        self.sb_font_size = Qt.QSpinBox()
        self.sb_font_size.setRange(5, 40)
        self.sb_font_size.setValue(12)                                   # +++
        self.sb_font_size.valueChanged.connect(self.fontSizeChanged)

        self.text_edit = Qt.QTextEdit()
        self.comboBox  = Qt.QComboBox()
        self.comboBox.addItem('Times New Roman')
        self.comboBox.addItem('Calibri')
        self.comboBox.addItem('Arial')
        #self.comboBox.activated = self.fontChanged                      # ---
        self.comboBox.currentIndexChanged[str].connect(self.fontChanged) # +++


        self.sizeLabel = Qt.QLabel("Size of text: <b style='color: blue;'> 12 </b>")
        self.fontLabel = Qt.QLabel("Font of text: <b style='color: blue;'>Times New Roman</b>")

        layout = Qt.QVBoxLayout()
        layout.addWidget(self.sizeLabel)
        layout.addWidget(self.sb_font_size)
        layout.addWidget(self.fontLabel)
        layout.addWidget(self.comboBox)
        layout.addWidget(self.text_edit)

        central_widget = Qt.QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

        self.text_edit.setFocus()                                        # +++

        self.text_char_format = Qt.QTextCharFormat()
        self.text_char_format.setFont(Qt.QFont("Times New Roman"))
        self.text_char_format.setFontPointSize(12)
        self.setTextFormat(self.text_char_format)


    def fontSizeChanged(self, value):
        self.sizeLabel.setText("Size of text: <b style='color: blue;'> {} </b>".format(value))
        self.text_char_format.setFontPointSize(value)
        self.setTextFormat(self.text_char_format)

    def setTextFormat(self, text_char_format):
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():  
            cursor.select(Qt.QTextCursor.WordUnderCursor) 
        cursor.mergeCharFormat(text_char_format)
        self.text_edit.mergeCurrentCharFormat(text_char_format)

        self.text_edit.setFocus()                                         # +++

    def fontChanged(self , value):
        self.fontLabel.setText("Font of text: <b style='color: blue;'>{}</b>".format(value))
        self.text_char_format.setFont(Qt.QFont(value))                    # +++
        self.text_char_format.setFontPointSize(self.sb_font_size.value())
        self.setTextFormat(self.text_char_format)        


if __name__ == '__main__':
    app = Qt.QApplication([])
    MainWin = MainWindow()
    MainWin.show()
    app.exec()
