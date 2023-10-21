import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)

import numpy as np
import pickle
import os

import figure_handeler, data_loader, constants, entities, data_catalog, logbook, operations, data_handler

#to implement:
#make all operations working in this new system
#normalisation by division of gold
#range plots
#fitting?
#fermi level for photon ebergy scan? -> Chun does it manually for each hv measuerment
#log scale -> not supported by pcolorfast
#select area:
    #normalise based on some selected area?
#symmetrise based on a reference?
#phi rotation in k convert?
#the inital start cut position

#Bugs:
#binding energy plots are transposed with respect to kinetic energy
#multiple file photon energy scan only seem to wor for evenly spaced energy scans
#cursor not showing at the beginnig
#figure changes colour for new pop up -> send self instead of just self.ax

#stuff:
#bg subtract (there may be angle dependence: bg_matt, bg_fermi)
#normalisation:
    #1) by number of sweeps (can chekc the BG above FL to check for number of sweeps),
    #2) MDC/EDC cuts divided by max value (fake data, just to enhance)

class GUI():#master Gui
    def __init__(self):
        self.size = constants.window_size
        self.window = tk.Tk()
        self.window.title('ARpest')
        self.window.state('zoomed')
        self.window.configure(background='white')
        self.design()

        self.notebook()
        self.open_botton()

        self.start_path = constants.start_path
        self.start_screen = Start_screen(self)
        self.pop = []

    def design(self):
        self.style = tk.ttk.Style()
        self.style.theme_use('alt')
        self.style.configure('TButton', background = 'white', foreground = 'black', borderwidth=1, focusthickness=3, focuscolor='none')

        self.style.map('gold.TButton', background=[('active','gold')])#when hovering
        self.style.configure('gold.TButton', background = 'gold', foreground = 'black', borderwidth=1, focusthickness=3, focuscolor='none')

        self.style.map('royalblue1.TButton', background=[('active','Royalblue1')])#when hovering
        self.style.configure('royalblue1.TButton', background = 'Royalblue1', foreground = 'black', borderwidth=1, focusthickness=3, focuscolor='none')

        self.style.map('toggle.TButton', background=[('active','powderblue')])#when hovering
        self.style.configure('toggle.TButton', background = 'powderblue', foreground = 'black', borderwidth=1, focusthickness=3, focuscolor='none')

        self.style.configure('TFrame', background='white')#makes th frame where plots are white
        self.style.map('TNotebook.Tab', background= [("selected", "white")])#makes the selected tab white
        self.style.configure("TNotebook", background= 'white')#makes ther notebook bg white

        self.style.configure("TScale", background="white")#makes ther notebook bg white

        #self.style.configure('TCheckbutton',indicatorbackground="black", indicatorforeground="white",background="white", foreground="white")
        #self.style.map('TCheckbutton', foreground=[('disabled', 'blue'),('selected', 'blue'),('!selected', 'grey')],background=[("active", "white")])
        #self.style.configure("TMenubutton", background="white")

    def notebook(self):
        self.notebook = tk.ttk.Notebook(master = self.window,width=self.size[0],height=self.size[1])#to make tabs
        self.notebook.pack()

    def open_botton(self):
        botton = tk.ttk.Button(self.window,text='open',command=self.open_file,style='royalblue1.TButton')
        botton.place(x = 700, y = 0)

    def open_file(self):
        files = tk.filedialog.askopenfilenames(initialdir = self.start_path ,title='data')
        if not files: return
        for file in files:
            self.tab = Data_tab(self,file)
        idx = file.rfind('/')+1
        self.start_path = file[:idx]#save the folder path so you start here next time

    def run(self):
        self.window.mainloop()

    def pop_up(self,**kwarg):#called from figure right click or colour bar: combine with the datatab one
        if not self.pop:#if empty
            size_string = kwarg['size']#depends on colur bar or figure
            size = size_string.split(',')
            sizes = {'size':[float(size[0]),float(size[1])],'top':kwarg['top'],'left':kwarg['left'],'right':kwarg['right'],'bottom':kwarg['bottom']}

            lim_string = self.tab.overviews[0].operations.fig_lim_entry.get()#it returns a string
            lim_string2 = lim_string.split(';')
            lim_x = lim_string2[0].split(',')
            lim_y = lim_string2[1].split(',')

            for index, x in enumerate(lim_x):
                if x == 'None':
                    lim_x[index] = None
                else:
                    lim_x[index] = float(x)

            for index, y in enumerate(lim_y):
                if y == 'None':
                    lim_y[index] = None
                else:
                    lim_y[index] = float(y)

            label_string = self.tab.overviews[0].operations.fig_label_entry.get()#it returns a string
            label = label_string.split(',')

            self.pop.append(Pop_up(self,sizes,[lim_x,lim_y],label))

class Start_screen():#should add general information and such
    def __init__(self,gui):
        self.gui = gui
        self.define_tab()
        self.instruments = ['Bloch','I05','SIS','URANOS']
        self.define_dropdowns()

    def define_tab(self):
        self.tab = tk.ttk.Frame(self.gui.notebook)
        self.gui.notebook.add(self.tab, text = 'Settings')

    def define_dropdowns(self):
        self.instrument = tk.StringVar()
        self.instrument.set(self.instruments[0])
        drop = tk.OptionMenu(self.tab,self.instrument,*self.instruments)
        drop.config(bg = "white")
        drop.place(x = 100, y = 300)

class Data_tab():#holder for overview tabs. The data is stored here
    def __init__(self, gui, file):
        self.gui = gui
        self.define_tab(file)
        self.define_notebook()
        self.save_botton()
        data = self.define_data_loader(file)
        self.load_overviews(data)
        self.gui.notebook.select(self.tab)
        self.pop = []

    def load_overviews(self, loaded_data):
        self.overviews = []
        for data in loaded_data:
            self.overviews.append(Overview(self, data))#automatically open overview

    def define_data_loader(self, file):#loading data
        self.data_loader = getattr(data_loader, self.gui.start_screen.instrument.get())(self)#make an object based on string
        data = self.data_loader.load_data(file)
        if data != None: return data#it means it succeeds. else, try another one

        for instrument in self.gui.start_screen.instruments:
            if instrument == self.gui.start_screen.instrument.get(): continue#skip the one already tried
            self.data_loader = getattr(data_loader, instrument)(self)#make an object based on string
            data = self.data_loader.load_data(file)
            if data != None: #sucess
                self.gui.start_screen.instrument.set(instrument)
                return data

    def define_notebook(self):
        self.notebook = tk.ttk.Notebook(master=self.tab,width=self.gui.size[0], height=self.gui.size[1])#to make tabs
        self.notebook.pack()

    def define_tab(self,file):
        idx = file.rfind('/')+1
        self.name = file[idx:]#used in overview
        self.tab = tk.ttk.Frame(self.gui.notebook)
        self.gui.notebook.add(self.tab, text = self.name)

    def append_tab(self,data):
        self.overviews.append(Overview(self, data))

    def save_botton(self):
        botton = tk.ttk.Button(self.tab,text='save',command=self.save, style='gold.TButton')
        botton.place(x = 1400, y = 750)

    def save(self):#things to save
        path = tk.filedialog.asksaveasfile(initialdir = self.gui.start_path ,title='data',initialfile=self.name)
        os.remove(path.name)#tk inter automatically makes a file. So this should be deleted becasuse we wil lmake a file with pickle
        all_data = []
        save_data = {}
        for index, overview in enumerate(self.overviews):
            overview.figure_handeler.save()

            save_data = {'int_range':overview.figure_handeler.int_range,'cmap':overview.figure_handeler.cmap,'instrument':self.gui.start_screen.instrument.get(),
            'colour_scale':overview.operations.color_scale.get(),'fig_lim_entry':overview.operations.fig_lim_entry.get(),'fig_size_entry':overview.operations.fig_size_entry.get(),
            'fig_label_entry':overview.operations.fig_label_entry.get(),'colourbar_size_entry':overview.operations.colourbar_size_entry.get(),'colourbar_orientation':overview.operations.colourbar_orientation.configure('text')[-1],
            'vlim':overview.operations.vlim_entry.get(),'colourbar_margines':{margin:overview.operations.colourbar_margines[margin].get() for margin in overview.operations.colourbar_margines.keys()},
            'fig_margines':{margin:overview.operations.fig_margines[margin].get() for margin in overview.operations.fig_margines.keys()},'arithmetic_x':overview.operations.arithmetic['x'].get(),
            'arithmetic_y':overview.operations.arithmetic['y'].get(),'data_stack_index':overview.data_handler.index}

            save_data.update(self.save_figure_specifics(overview))#combine the dicts
            #save_data.update(overview.data_handler.data.save())#combine the dicts
            overview.data_handler.data_stack[0].save(save_data)
            #save_data['data_stack'] = overview.data_handler.data_stack#a list of File objects
            all_data.append(overview.data_handler.data_stack)

        with open(path.name + '.okf', "wb") as outfile:
            pickle.dump(all_data, outfile)

    def save_figure_specifics(self, overview):
        data ={}
        for key in overview.figure_handeler.figures.keys():
            data[type(overview.figure_handeler.figures[key]).__name__ + 'cut_index'] = overview.figure_handeler.figures[key].cut_index
            data[type(overview.figure_handeler.figures[key]).__name__ + 'cursor_pos'] = overview.figure_handeler.figures[key].cursor.pos
        return data

    def pop_up(self,**kwarg):#called from figure right click or colour bar
        size_string = kwarg['size']#depends on colur bar or figure
        size = size_string.split(',')
        sizes = {'size':[float(size[0]),float(size[1])],'top':kwarg['top'],'left':kwarg['left'],'right':kwarg['right'],'bottom':kwarg['bottom']}

        lim_string = self.overviews[0].operations.fig_lim_entry.get()#it returns a string
        lim_string2 = lim_string.split(';')
        lim_x = lim_string2[0].split(',')
        lim_y = lim_string2[1].split(',')

        for index, x in enumerate(lim_x):
            if x == 'None':
                lim_x[index] = None
            else:
                lim_x[index] = float(x)

        for index, y in enumerate(lim_y):
            if y == 'None':
                lim_y[index] = None
            else:
                lim_y[index] = float(y)

        label_string = self.overviews[0].operations.fig_label_entry.get()#it returns a string
        label = label_string.split(',')

        self.pop.append(Pop_up(self,sizes,[lim_x,lim_y],label))

class Overview():
    def __init__(self, data_tab, data):
        self.data_tab = data_tab
        self.add_tab(type(self).__name__)
        self.data_handler = data_handler.Data_handler(self, data)#will have the data
        self.make_figure()#figure_handler
        self.operations = operations.Operations(self)
        self.logbook = logbook.Logbook(self)
        self.data_catalog = data_catalog.Data_catalog(self)
        self.figure_handeler.redraw()
        self.data_tab.notebook.select(self.tab)
        self.close_botton()

    def close_botton(self):#to close the datatab
        botton = tk.ttk.Button(self.tab,text='close',command = self.close)
        botton.place(x = 1400, y = 800)

    def close(self):#implement so that if it is only one overview left, close the datatab
        self.data_tab.notebook.forget(self.tab)
        self.data_tab.overviews.remove(self)
        if not self.data_tab.overviews:#if no overivew left
            self.data_tab.gui.notebook.forget(self.data_tab.tab)

    def add_tab(self,name):
        self.tab = tk.ttk.Frame(self.data_tab.notebook, style='My.TFrame')
        self.data_tab.notebook.add(self.tab,text = name)

    def make_figure(self):
        if self.data_handler.data.get_data('zscale') is None or len(self.data_handler.data.get_data('zscale')) == 1:#2D data
            self.figure_handeler = figure_handeler.Twodimension(self)
        else:#3D data
            self.figure_handeler = figure_handeler.Threedimension(self)

class Pop_up():#the pop up window
    def __init__(self, data_tab, sizes, lim, label):
        self.data_tab = data_tab
        self.fig = plt.Figure(figsize = sizes['size'])
        self.ax = self.fig.add_subplot(111)
        self.lim = lim#will  be updated from figure right clicj
        self.ax.set_xlabel(label[0])
        self.ax.set_ylabel(label[1])
        self.fig.subplots_adjust(top = float(sizes['top']),left = float(sizes['left']),right = float(sizes['right']), bottom = float(sizes['bottom']))
        self.popup = tk.Toplevel()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.popup)
        self.canvas.get_tk_widget().pack()
        NavigationToolbar2Tk(self.canvas, self.popup).update()
        self.canvas._tkcanvas.pack()

        self.popup.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.popup.focus_set()

    def set_lim(self):#called from figure ricj click
        self.ax.set_xbound(self.lim[0])
        self.ax.set_ybound(self.lim[1])

    def set_vlim(self,vmin,vmax):
        self.graph.set_clim(vmin = vmin, vmax = vmax)#all graphs have common have comon vmax and vmin

    def on_closing(self):
        self.popup.destroy()
        self.data_tab.pop.remove(self)


if __name__ == "__main__":
    gui = GUI()
    gui.run()
