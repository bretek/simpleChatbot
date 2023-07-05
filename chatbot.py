import requests
import time
import os
import dotenv
import random
from PyQt6.QtWidgets import QMainWindow, QApplication, QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QPushButton
from PyQt6.QtCore import QSize, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QIcon

dotenv.load_dotenv('./secrets.env')
API_TOKEN = os.getenv('API_TOKEN')
API_URL = "https://api-inference.huggingface.co/models/bigscience/bloom"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

global questions
questions = []
global chat_responses
chat_responses = []

def query(payload):
	response = requests.post(API_URL, headers=headers, json=payload)
	return response.json()

def get_response(statement, chat_log, mood):
    global questions
    global chat_responses

    #format input
    payload = {"inputs": chat_log + "User: " + str(statement) + "\n" + mood + "Chatbot: "}
    #query api
    output = query(payload)
    #format response
    for response in output:
        response = response["generated_text"]
        response = response[response.find("User: " + str(statement) + "\n") + len("User: " + str(statement) + "\n"):response.find('User: ', response.find("User: " + str(statement) + "\n") + len("User: " + str(statement) + "\n"))]
        response = response[response.find(mood) + len(mood):]
        response = response.rstrip()

        if len(chat_responses) > 0:
            if response == chat_responses[-1] or response == statement:
                response = get_response(statement, chat_log, mood + str(random.randint(0,10000)))

        questions.append(statement)
        chat_responses.append(response)

        return response

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        #set up window properties
        self.setWindowTitle("Chatbot")
        self.resize(QSize(800, 400))

        #layout window
        wid = QWidget(self)
        self.setCentralWidget(wid)

        self.chat_window = QLabel(self)
        self.chat_window.setText("")
        self.chat_window.setWordWrap(True)

        self.chat_scroll = QScrollArea(self)
        self.chat_scroll.setWidget(self.chat_window)
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.verticalScrollBar().rangeChanged.connect(self.scrollToBottom)
        self.chat_scroll.setMinimumWidth(400)

        self.chat_input = QLineEdit(self)

        self.chat_input_enter = QPushButton(self)
        self.chat_input_enter.setIcon(QIcon.fromTheme("edit-undo"))

        self.bot_image = QLabel(self)
        self.bot_image.setPixmap(QPixmap("happy_bot.png"))
        self.bot_image.show()

        self.chat_input_layout = QHBoxLayout()
        self.chat_input_layout.addWidget(self.chat_input)
        self.chat_input_layout.addWidget(self.chat_input_enter)

        self.text_layout = QVBoxLayout()
        self.text_layout.addWidget(self.chat_scroll)
        self.text_layout.addLayout(self.chat_input_layout)

        self.chat_layout = QHBoxLayout()
        self.chat_layout.addLayout(self.text_layout)
        self.chat_layout.addWidget(self.bot_image)

        wid.setLayout(self.chat_layout)

        #alignments
        self.chat_window.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_input.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.chat_scroll.setAlignment(Qt.AlignmentFlag.AlignTop)

        #connect widget functions
        self.chat_input.returnPressed.connect(self.text_entered)
        self.chat_input_enter.clicked.connect(self.text_entered)

        #variables
        self.response_thread = None
        self.loading_thread = None

    def text_entered(self):
        if self.response_thread == None or not self.response_thread.isRunning():
            text = self.chat_input.text()
            self.response_thread = GetResponseThread(self.chat_window, text, self.chat_window.text())
            self.response_thread.updateChatSignal.connect(self.update_chat_text)
            self.response_thread.gotResponseSignal.connect(self.kill_loading_indicator)
            self.chat_window.setText(self.chat_window.text() + '\nUser: ' + text)

            self.loading_thread = LoadingIndicatorUpdateThread(self.chat_window)
            self.loading_thread.updateChatWindowSignal.connect(self.update_chat_text)
            self.loading_thread.start()

            self.chat_scroll.setWidget(self.chat_window)
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
            self.chat_input.clear()
            self.response_thread.start()

    def scrollToBottom (self, minVal=None, maxVal=None):
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def update_chat_text(self, text):
        self.chat_window.setText(text)
        self.chat_scroll.setWidget(self.chat_window)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def kill_loading_indicator(self):
        self.loading_thread.active = False

class GetResponseThread(QThread):
    updateChatSignal = pyqtSignal(str)
    gotResponseSignal = pyqtSignal()

    def __init__(self, chat_window, statement, chatlog):
        QThread.__init__(self)
        self.chat_window = chat_window
        self.statement = statement
        self.chatlog = chatlog

    def __del__(self):
        self.wait()

    def run(self):
        response = get_response(self.statement, self.chatlog, 'talkative and inquisitive customer service ')
        self.gotResponseSignal.emit()
        time.sleep(0.2)
        self.updateChatSignal.emit(self.chat_window.text() + '\n' + response)

class LoadingIndicatorUpdateThread(QThread):
    updateChatWindowSignal = pyqtSignal(str)

    def __init__(self, chat_window):
        QThread.__init__(self)
        self.indicator = '...'
        self.indicator_index = len(self.indicator)
        self.chat_window = chat_window
        self.active = True
    
    def __del__(self):
        self.wait()

    def run(self):
        self.updateChatWindowSignal.emit(self.chat_window.text() + '\nChatbot: ' + self.indicator)
        time.sleep(0.1)

        while(self.active):
            text = list(self.indicator)
            if self.indicator_index > 0:
                text[self.indicator_index - 1] = '.'
            if self.indicator_index == len(self.indicator):
                self.indicator_index = 0
            else:
                text[self.indicator_index] = 'o'
                self.indicator_index += 1

            text = 'Chatbot: ' + "".join(text)

            self.updateChatWindowSignal.emit(self.chat_window.text()[:len(self.chat_window.text())-len(text)-1] + '\n' +  text)

            time.sleep(0.2)

        self.updateChatWindowSignal.emit(self.chat_window.text()[:len(self.chat_window.text())-len(text)-1])

#create window and show it
app = QApplication([])

window = MainWindow()
window.show()

app.exec()
