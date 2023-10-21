import tkinter as tk
from tkinter import ttk

class Button():
    def __init__(self, operations, tab, type, iterations = ['horizontal','vertical'], width = 10, command = None, style = 'toggle.TButton'):
        default = operations.overview.data_handler.data.get(type, iterations[0])
        self.iterations = iterations
        self.box = tk.ttk.Button(tab, text = default, command = self.press, width = width, style = style)#which figures shoudl have access to this?
        self.index = 0
        self.command = command

    def press(self):
        self.index += 1
        if self.index >= len(self.iterations):
            self.index = 0
        state = self.iterations[self.index]
        self.box.configure(text=state)
        if self.command:
            self.command()

    def place(self, x, y):
        self.box.place(x = x,y = y)

    def configure(self,text):
        return self.box.configure(text)
