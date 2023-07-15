import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
#from matplotlib import transforms

from argparse import Namespace
import numpy as np

import figure_handeler, data_loader

#namespace or dict?

#to implement:
#make same y,x limits/zoom
#labels
#colour bar (where?)
#rotate figure?
#fermi level for photon ebergy scan?
#kz -> convert to k, correct fermi level without interpolation?
#log scale
#make so that mouse appears automatically at the begining

#Bugs:
#the slit issue
#multiple file photon energy scan only seem to wor for evenly spaced energy scans
#(array length problem/uniform shape problem)
#probably need to the axis corrections for each energy to make a 3D data (for FS only)

#stuff:
#angle2k
#bg subtract (there may be angle dependence: bg_matt, bg_fermi)
#2nd derivative
#normalisation:
    #1) by number of sweeps (can chekc the BG above FL to check for number of sweeps),
    #2) MDC/EDC cuts divided by max value (fake data, just to enhance)

class GUI():#master Gui
    def __init__(self):
        self.size = [1920,1080]
        self.window = tk.Tk()
        self.window.title('Apest')
        self.window.state('zoomed')
        self.window.configure(background='white')
        self.design()

        self.tabs()
        self.botton()

        self.pop = None
        self.start_path = '/Users/olakenjiforslund/Library/CloudStorage/OneDrive-Chalmers/Work/Research/Experiment/Data/Photons'
        self.start_screen = Start_screen(self)

    def design(self):
        self.style = tk.ttk.Style()
        self.style.theme_use('alt')
        self.style.configure('TButton', background = 'white', foreground = 'black', borderwidth=1, focusthickness=3, focuscolor='none')
        self.style.map('TButton', background=[('active','white')])
        self.style.configure('TFrame', background='white')#makes th frame where plots are white
        self.style.map('TNotebook.Tab', background= [("selected", "white")])#makes the selected tab white
        self.style.configure("TNotebook", background= 'white')#makes ther notebook bg white
        self.style.configure('TCheckbutton',indicatorbackground="black", indicatorforeground="white",background="white", foreground="white")
        self.style.map('TCheckbutton', foreground=[('disabled', 'blue'),('selected', 'blue'),('!selected', 'grey')],background=[("active", "white")])
        self.style.configure("TMenubutton", background="white")

    def tabs(self):
        self.notebook = tk.ttk.Notebook(master = self.window,width=self.size[0],height=self.size[1])#to make tabs
        self.notebook.pack()

    def botton(self):
        botton = tk.ttk.Button(self.window,text='open',command=self.open_file)
        botton.place(x = 700, y = 0)

    def open_file(self):
        files = tk.filedialog.askopenfilenames(initialdir = self.start_path ,title='data')
        for file in files:
            self.tab = Data_tab(self,file)
        idx = file.rfind('/')+1
        self.start_path = file[:idx]#save the folder path so you start here next time

    def run(self):
        self.window.mainloop()
        #while True:
            #self.window.update_idletasks()
            #self.window.update()

    def pop_up(self):#called from figure right click
        if self.pop == None:
            self.pop = Pop_up(self)

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

class Data_tab():#holder for overview and analysis tabs. The data is stored here
    def __init__(self,gui,file):
        self.gui = gui
        data = self.define_data_loader(file)#try the selected instrument. If it doesn't work, try the other ones
        self.define_tab(file)
        self.define_notebook()
        self.close_bottom()
        self.overview = Overview(self,data)#automatically open overview

    def define_data_loader(self, file):
        self.data_loader = getattr(data_loader, self.gui.start_screen.instrument.get())(self)#make an object based on string
        data = self.data_loader.load_data(file)
        if data != None: return data#it means it succeeds. else, try another one

        for instrument in self.gui.start_screen.instruments:
            if instrument == self.gui.start_screen.instrument.get(): continue#skip the one alreadt tried
            self.data_loader = getattr(data_loader, instrument)(self)#make an object based on string
            data = self.data_loader.load_data(file)
            if data != None: return data

    def define_notebook(self):
        self.notebook = tk.ttk.Notebook(master=self.tab,width=self.gui.size[0], height=self.gui.size[1])#to make tabs
        self.notebook.pack()

    def define_tab(self,file):
        idx = file.rfind('/')+1
        self.name = file[idx:]#used in overview
        self.tab = tk.ttk.Frame(self.gui.notebook)
        self.gui.notebook.add(self.tab,text=self.name)

    def append_tab(self,data):
        self.analysis = Analysis(self,data)

    def close_bottom(self):#to close the datatab
        botton = tk.ttk.Button(self.tab,text='close',command=self.close)
        botton.place(x =1400, y = 850)

    def close(self):
        self.tab.destroy()

class Subtab():
    def __init__(self,data_tab,data):
        super().__init__()
        self.data_tab = data_tab
        self.data = data
        self.int_range = 0
        self.add_tab(type(self).__name__)
        self.cmap = 'RdYlBu_r'#default colour scale

    def add_tab(self,name):
        self.tab = tk.ttk.Frame(self.data_tab.notebook, style='My.TFrame')
        self.data_tab.notebook.add(self.tab,text=name)

class Overview(Subtab):
    def __init__(self,data_tab,data):
        super().__init__(data_tab,data)
        self.make_figure()
        self.operations = Operations(self)
        self.logbook()
        self.append_data_botton()
        self.append_data(self.data_tab.name)
        self.define_combine_data()

    def make_figure(self):
        if self.data.zscale is None or len(self.data.zscale)==1:#2D data
            self.figure_handeler = figure_handeler.Twodimension(self)
        else:#3D data
            self.figure_handeler = figure_handeler.Threedimension(self)

    def draw(self):
        self.figure_handeler.draw()

    def redraw(self):
        self.figure_handeler.redraw()

    def logbook(self):
        columns=[]
        data=[]
        for key in self.data.metadata:
            columns.append(key)
            data.append(self.data.metadata[key])

        tree = tk.ttk.Treeview(self.tab,columns=columns,show='headings',height=2)
        verscrlbar = tk.ttk.Scrollbar(self.tab,orient ="horizontal",command = tree.xview)
        #verscrlbar.place(x = 900, y = 0, width=200+20)
        tree.configure(xscrollcommand=verscrlbar.set)

        for texts in columns:
            tree.heading(texts,text=texts)
            tree.column(texts,width=100,stretch=False)
        tree.insert('',tk.END,values=data)
        tree.place(x = 890, y = 0, width=610)

    def append_data_botton(self):#called frin init
        button = tk.ttk.Button(self.tab, text="append data", command = self.append_method)
        button.place(x = 890, y = 470)
        self.data_catalog()

    def data_catalog(self):#make a box containig data
        self.catalog = tk.ttk.Treeview(self.tab,columns='Data',show='headings',height=2)
        verscrlbar = tk.ttk.Scrollbar(self.tab,orient ="vertical",command = self.catalog.yview)
        #verscrlbar.place(x = 900, y = 0, width=200+20)
        self.catalog.heading('Data')
        self.catalog.configure(yscrollcommand=verscrlbar.set)
        self.catalog.place(x = 890, y = 500, width=300,height=300)

    def append_method(self):
        files = tk.filedialog.askopenfilenames(initialdir=self.data_tab.gui.start_path ,title='data')
        for file in files:
            self.append_data(file)

    def append_data(self,file):
        idx = file.rfind('/')+1
        name = file[idx:]
        self.catalog.insert('',tk.END,values=name)

    def define_combine_data(self):
        button = tk.ttk.Button(self.tab, text="combine data", command = self.combine_data)
        button.place(x = 1080, y = 470)

    def combine_data(self):#combining and putting the data in the data catalog: photon energy as x, angle as  y, kintex energy as z, intensity as data (3D)
        indices = self.catalog.selection()
        hv = []
        for num, index in enumerate(indices):
            data_name = self.catalog.item(index)['values'][0]
            loadded_data = getattr(data_loader, self.data_tab.gui.start_screen.instrument.get())(self.data_tab)#make an object based on string
            scan_data = loadded_data.load_data(self.data_tab.gui.start_path + '/' + data_name)
            #scan_data = dl.load_data(self.data_tab.gui.start_path + '/' + data_name)#store the data in the catalog into a dict
            hv.append(scan_data.metadata['hv'])#the photon energy
            if num == 0:
                int = np.atleast_3d(np.transpose(scan_data.data[0]))
            else:
                int = np.append(int,np.atleast_3d(np.transpose(scan_data.data[0])),axis=2)

        scan_data.metadata['hv'] = hv
        new_data = Namespace(xscale=np.array(hv), yscale=scan_data.yscale,zscale=scan_data.xscale,data=int,metadata=scan_data.metadata)#add meta data
        tab = self.data_tab.append_tab(new_data)

class Operations():
    def __init__(self,overview):
        self.overview = overview
        self.make_box()
        self.define_dropdowns()
        self.define_BG()
        self.define_int_range()
        self.define_fermilevel()
        self.define_colour_scale()
        self.define_kz()
        self.define_k_convert()
        self.define_symmetrise()
        self.define_derivative()
        self.define_reset()
        self.define_smooth()

    def make_box(self):#make a box with operations options on the figures
        self.notebook = tk.ttk.Notebook(master=self.overview.tab,width=610, height=300)#to make tabs
        self.notebook.place(x=890,y=80)
        operations = ['General','Operations']
        self.operation_tabs = {}
        for operation in operations:
            self.operation_tabs[operation] = tk.ttk.Frame(self.notebook, style='My.TFrame')
            self.notebook.add(self.operation_tabs[operation],text=operation)

    def define_int_range(self):
        scale = tk.ttk.Scale(self.operation_tabs['General'],from_=0,to=5,orient='horizontal',command=self.update_line_width)#
        scale.place(x = 0, y = 50)
        label=ttk.Label(self.operation_tabs['General'],text='int. range',background='white',foreground='black')
        label.place(x = 0, y = 30)

    def update_line_width(self,value):#the slider calls it
        self.overview.int_range = int(float(value))
        self.overview.figure_handeler.update_line_width()

    def define_colour_scale(self):
        self.color_scale = tk.ttk.Scale(self.operation_tabs['General'],from_=0,to=100,orient='horizontal',command=self.overview.figure_handeler.update_colour_scale,value = 100)#
        self.color_scale.place(x = 0, y = 100)
        label=ttk.Label(self.operation_tabs['General'],text='colour scale',background='white',foreground='black')
        label.place(x = 0, y = 80)

    def define_dropdowns(self):
        commands = ['RdYlBu_r','RdBu_r','terrain','binary', 'binary_r'] + sorted(['Spectral_r','bwr','coolwarm', 'twilight_shifted','twilight_shifted_r', 'PiYG', 'gist_ncar','gist_ncar_r', 'gist_stern','gnuplot2', 'hsv', 'hsv_r', 'magma', 'magma_r', 'seismic', 'seismic_r','turbo', 'turbo_r'])
        dropvar = tk.StringVar(self.operation_tabs['General'])
        dropvar.set('colours')
        drop = tk.OptionMenu(self.operation_tabs['General'],dropvar,*commands,command = self.select_drop)
        drop.config(bg="white")
        drop.place(x = 0, y = 0)

    def select_drop(self,event):
        self.overview.cmap = event
        self.overview.draw()

    def define_BG(self):#generate botton, it will run the figure method
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="BG", command = self.overview.figure_handeler.subtract_BG)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 0)
        self.BG_choise()

    def BG_choise(self):
        choises = ['horizontal','vertical','EDC']
        self.checkbox = {}
        for index, choise in enumerate(choises):
            self.checkbox[choise] = tk.IntVar()
            tk.ttk.Checkbutton(self.operation_tabs['Operations'], text=choise, variable=self.checkbox[choise]).place(x=120,y=30*index)

    def define_derivative(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="2nd derivative", command = self.overview.figure_handeler.derivative)#which figures shoudl have access to this?
        button_calc.place(x = 230, y = 0)
        self.derivative_choise()

    def derivative_choise(self):
        choises = ['horizontal','vertical']
        self.checkbox_drivative = {}
        for index, choise in enumerate(choises):
            self.checkbox_drivative[choise] = tk.IntVar()
            tk.ttk.Checkbutton(self.operation_tabs['Operations'], text=choise, variable=self.checkbox_drivative[choise]).place(x=350,y=30*index)

    def define_reset(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="reset", command = self.overview.figure_handeler.reset)#which figures shoudl have access to this?
        button_calc.place(x = 480, y = 0)

    def define_fermilevel(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Fermi level", command = self.overview.figure_handeler.fermi_level)
        button_calc.place(x=0,y=70)

    def define_kz(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="kz", command = self.overview.figure_handeler.kz_convert)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 100)

    def define_k_convert(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="k convert", command = self.overview.figure_handeler.k_convert)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 130)

    def define_symmetrise(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="symmetrise", command = self.overview.figure_handeler.symmetrise)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 160)

    def define_smooth(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="smooth", command = self.overview.figure_handeler.smooth)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 190)
        self.smooth_choise()

    def smooth_choise(self):
        choises = ['horizontal','vertical']
        self.checkbox_smooth = {}
        for index, choise in enumerate(choises):
            self.checkbox_smooth[choise] = tk.IntVar()
            tk.ttk.Checkbutton(self.operation_tabs['Operations'], text=choise, variable=self.checkbox_smooth[choise]).place(x=150,y=190 + 30*index)

class Analysis(Overview):
    def __init__(self,data_tab,data):
        super().__init__(data_tab,data)

class Pop_up():#the pop up window
    def __init__(self,gui):
        self.gui = gui
        self.fig = plt.Figure(figsize=(3.3,3.3))
        self.ax = self.fig.add_subplot(111)

        self.popup = tk.Toplevel()
        self.pop_canvas = FigureCanvasTkAgg(self.fig, master=self.popup)
        self.pop_canvas.get_tk_widget().pack()
        NavigationToolbar2Tk(self.pop_canvas, self.popup).update()
        self.pop_canvas._tkcanvas.pack()

        self.popup.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.popup.focus_set()

    def on_closing(self):
        self.popup.destroy()
        self.gui.pop = None

if __name__ == "__main__":
    gui = GUI()
    gui.run()
