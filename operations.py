import tkinter as tk
from tkinter import ttk
import numpy as np

import entities

class Operations():
    def __init__(self, overview):
        self.overview = overview
        self.make_box()

        #general
        self.define_dropdowns()
        self.define_BG()
        self.define_int_range()
        self.define_crusorslope()
        self.define_crusor_position()
        self.define_vlim()
        self.define_set_vlim()
        self.define_grid()

        #operations
        self.define_colour_scale()
        self.define_fermilevel()
        self.define_kz()
        self.define_k_convert()
        self.define_symmetrise()
        self.define_derivative()
        self.define_smooth()
        self.define_curvature()
        self.define_normalise()
        self.define_orientation_botton()
        self.define_integrate()
        self.define_EF_correction()

        #figures
        self.define_fig_size()
        self.define_colourbar_size()
        self.define_fig_lim()
        self.define_fig_label()
        self.define_colourbar_orientation()
        self.define_margines()

        #Arithmetic
        self.define_multiply()

        #clip
        self.define_c_clip()

    def make_box(self):#make a box with operations options on the figures
        self.notebook = tk.ttk.Notebook(master=self.overview.tab,width=610, height=300)#to make tabs
        self.notebook.place(x = 890, y = 80)
        operations = ['General','Operations','Figures','Arithmetic','Clip']
        self.operation_tabs = {}
        for operation in operations:
            self.operation_tabs[operation] = tk.ttk.Frame(self.notebook, style = 'My.TFrame')
            self.notebook.add(self.operation_tabs[operation],text=operation)

    #general tab
    def define_int_range(self):
        scale = tk.ttk.Scale(self.operation_tabs['General'],from_ = 0,to = 200,orient='horizontal',command=self.update_line_width)#
        scale.place(x = 0, y = 50)
        label = ttk.Label(self.operation_tabs['General'],text='int. range',background='white',foreground='black')
        label.place(x = 0, y = 30)
        self.label = ttk.Label(self.operation_tabs['General'],text = self.overview.figure_handeler.int_range,background='white',foreground='black')#need to save it to updat the number next to the slide
        self.label.place(x = 100, y = 50)
        scale.set(self.overview.figure_handeler.int_range)#need to be after self.label

    def update_line_width(self,value):#the slider calls it
        self.overview.figure_handeler.int_range = int(float(value))
        self.overview.figure_handeler.update_line_width()
        self.label.configure(text = str(1 + 2*int(float(value))))#update the number next to int range slide

    def define_colour_scale(self):
        self.color_scale = tk.ttk.Scale(self.operation_tabs['General'],from_=0,to=100,orient='horizontal',command = self.overview.figure_handeler.update_colour_scale,value = self.overview.data_handler.file.save_dict.get('colour_scale',100))#
        self.color_scale.place(x = 0, y = 100)
        label=ttk.Label(self.operation_tabs['General'],text='colour scale',background='white',foreground='black')
        label.place(x = 0, y = 80)
        self.label3 = ttk.Label(self.operation_tabs['General'],text = round(self.overview.data_handler.file.save_dict.get('colour_scale',100),1),background='white',foreground='black')#need to save it to updat the number next to the slide
        self.label3.place(x = 100, y = 100)

    def define_dropdowns(self):
        commands = ['RdYlBu_r','RdBu_r','terrain','binary', 'binary_r'] + sorted(['Spectral_r','bwr','coolwarm', 'twilight_shifted','twilight_shifted_r', 'PiYG', 'gist_ncar','gist_ncar_r', 'gist_stern','gnuplot2', 'hsv', 'hsv_r', 'magma', 'magma_r', 'seismic', 'seismic_r','turbo', 'turbo_r'])
        dropvar = tk.StringVar(self.operation_tabs['General'])
        dropvar.set('colours')
        drop = tk.OptionMenu(self.operation_tabs['General'],dropvar,*commands,command = self.select_drop)
        drop.config(bg="white")
        drop.place(x = 0, y = 0)

    def define_crusorslope(self):
        scale = tk.ttk.Scale(self.operation_tabs['General'],from_=-45,to=45,orient='horizontal',command = self.overview.figure_handeler.figures['center'].cursor.update_slope,style="TScale")#
        scale.place(x = 0, y = 150)
        label=ttk.Label(self.operation_tabs['General'],text='slope',background='white',foreground='black')
        label.place(x = 0, y = 130)
        self.label2 = ttk.Label(self.operation_tabs['General'],text = str(0),background='white',foreground='black')#need to save it to updat the number next to the slide
        self.label2.place(x = 100, y = 150)

    def define_crusor_position(self):
        button_calc = tk.ttk.Button(self.operation_tabs['General'], text="reset position", command = self.overview.figure_handeler.figures['center'].cursor.reset_position)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 250)

    def select_drop(self,event):
        self.overview.figure_handeler.cmap = event
        self.overview.figure_handeler.draw()
        self.overview.figure_handeler.colour_bar.update()

    def define_vlim(self):
        self.vlim_entry = tk.ttk.Entry(self.operation_tabs['General'], width= 10)#
        default = self.overview.data_handler.file.save_dict.get('vlim','None,None')
        self.vlim_entry.insert(0, default)#default text
        self.vlim_entry.place(x = 150, y = 100)
        label = ttk.Label(self.operation_tabs['General'],text = 'colour limits',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 150, y = 80)

    def define_set_vlim(self):
        button = tk.ttk.Button(self.operation_tabs['General'], text="set colour limit", command = self.overview.figure_handeler.colour_bar.set_vlim)#which figures shoudl have access to this?
        button.place(x = 250, y = 100)

    def define_grid(self):
        self.grid_button = entities.Button(self, self.operation_tabs['General'],'grid_button',['grid on','grid off'], command = self.overview.figure_handeler.make_grid)
        self.grid_button.place(x = 150, y = 50)

    #operation tab
    def define_orientation_botton(self):
        self.orientation_botton = entities.Button(self, self.operation_tabs['Operations'],'orientation_botton',['horizontal','vertical'])
        self.orientation_botton.place(x = 350, y = 0)

    def define_derivative(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="2nd derivative", command = self.overview.figure_handeler.derivative)#which figures shoudl have access to this?
        button_calc.place(x = 350, y = 70)

    def define_smooth(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="smooth", command = self.overview.figure_handeler.smooth)#which figures shoudl have access to this?
        button_calc.place(x = 350, y = 100)

    def define_curvature(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Curvature", command = self.overview.figure_handeler.curvature)#which figures shoudl have access to this?
        button_calc.place(x = 350, y = 130)

    def define_BG(self):#generate botton, it will run the figure method
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="BG", command = self.overview.figure_handeler.subtract_BG)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 0)
        self.BG_orientation = entities.Button(self, self.operation_tabs['Operations'],'BG_orientation',['horizontal','vertical','EDC','bg Matt'])
        self.BG_orientation.place(x = 120, y = 0)

    def define_fermilevel(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Fermi level", command = self.overview.figure_handeler.fermi_level)
        button_calc.place(x = 0, y = 70)

    def define_kz(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="kz", command = self.overview.figure_handeler.kz_convert)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 100)

    def define_k_convert(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="k convert", command = self.overview.figure_handeler.k_convert)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 130)

    def define_symmetrise(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="symmetrise", command = self.overview.figure_handeler.symmetrise)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 160)

    def define_integrate(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="integrate", command = self.overview.figure_handeler.integrate)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 190)

    def define_EF_correction(self):
        botton = tk.ttk.Button(self.operation_tabs['Operations'], text="EF corr", command = self.overview.figure_handeler.EF_corr)#which figures shoudl have access to this?
        botton.place(x = 0, y = 250)

    def define_normalise(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Normalise slice", command = self.overview.figure_handeler.normalise)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 220)

    #figure tab
    def define_fig_size(self):
        self.fig_size_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 10)#
        default = self.overview.data_handler.file.save_dict.get('fig_size_entry','3.3,3.3')
        self.fig_size_entry.insert(0, default)#default text
        self.fig_size_entry.place(x = 0, y = 50)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'figure size',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 50)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_fig_size)#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 50)

    def define_fig_lim(self):
        self.fig_lim_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 20)#
        default = self.overview.data_handler.file.save_dict.get('fig_lim_entry','None,None;None,None')
        self.fig_lim_entry.insert(0, default)#default text
        self.fig_lim_entry.place(x = 0, y = 80)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'figure limits',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 80)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_fig_lim)#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 80)

    def define_fig_label(self):
        self.fig_label_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 10)#
        default = self.overview.data_handler.file.save_dict.get('fig_label_entry','x,y')
        self.fig_label_entry.insert(0, default)#default text
        self.fig_label_entry.place(x = 0, y = 110)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'figure label',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 110)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_fig_label)#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 110)

    def define_colourbar_size(self):
        self.colourbar_size_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 10)#
        default = self.overview.data_handler.file.save_dict.get('colorbar_size_entry','3.3,0.7')
        self.colourbar_size_entry.insert(0, default)#default text
        self.colourbar_size_entry.place(x = 0, y = 200)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'colourbar size',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 200)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_colorbar_size)#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 200)

    def define_colourbar_orientation(self):
        self.colourbar_orientation = entities.Button(self, self.operation_tabs['Figures'],'colourbar_orientation',['horizontal','vertical'])
        self.colourbar_orientation.place(x = 100, y = 200)

    def define_margines(self):
        margines = ['top','left','right','bottom']
        self.fig_margines = {}
        self.colourbar_margines = {}
        for index, margin in enumerate(margines):
            self.fig_margines[margin] = tk.ttk.Entry(self.operation_tabs['Figures'], width= 3)#
            self.colourbar_margines[margin] = tk.ttk.Entry(self.operation_tabs['Figures'], width= 3)#

            default = self.overview.data_handler.file.save_dict.get('fig_margines',{'top':0.93,'left':0.18,'right':0.97,'bottom':0.13})
            self.fig_margines[margin].insert(0, default[margin])#default text
            self.fig_margines[margin].place(x = 50 + 50*index, y = 20)
            label = ttk.Label(self.operation_tabs['Figures'],text = margin,background='white',foreground='black')#need to save it to updat the number next to the slide
            label.place(x = 50 + 50*index, y = 0)

            default = self.overview.data_handler.file.save_dict.get('colourbar_margines',{'top':0.9,'left':0.03,'right':0.96,'bottom':0.7})
            self.colourbar_margines[margin].insert(0, default[margin])#default text
            self.colourbar_margines[margin].place(x = 50 + 50*index, y = 170)
            label = ttk.Label(self.operation_tabs['Figures'],text = margin,background='white',foreground='black')#need to save it to updat the number next to the slide
            label.place(x = 50 + 50*index, y = 150)

    def reset_fig_lim(self):
        self.fig_lim_entry.delete(0, "end")
        self.fig_lim_entry.insert(0, 'None,None;None,None')#default text

    def reset_colorbar_size(self):
        self.colourbar_size_entry.delete(0, "end")
        self.colourbar_size_entry.insert(0, '3.3,0.7')#default text

    def reset_fig_size(self):
        self.fig_size_entry.delete(0, "end")
        self.fig_size_entry.insert(0, '3.3,3.3')#default text

    def reset_fig_label(self):
        self.fig_label_entry.delete(0, "end")
        self.fig_label_entry.insert(0, 'x,y')#default text

    #Arithmetic
    def define_multiply(self):
        self.arithmetic = {'x':None,'y':None}
        self.arithmetic_botton = {'x':None,'y':None}
        for index, dir in enumerate(self.arithmetic.keys()):
            self.arithmetic[dir] = tk.ttk.Entry(self.operation_tabs['Arithmetic'], width= 10)#
            default = self.overview.data_handler.file.save_dict.get('arithmetic_' + dir,'1')
            self.arithmetic[dir].insert(0, default)#default text
            self.arithmetic[dir].place(x = 0, y = 50 + index*20)
            label = ttk.Label(self.operation_tabs['Arithmetic'],text = dir + ' axis',background='white',foreground='black')#need to save it to updat the number next to the slide
            label.place(x = 200, y = 50 + index*20)

            label2 = ttk.Label(self.operation_tabs['Arithmetic'],text = '/',background='white',foreground='black')#need to save it to updat the number next to the slide
            label2.place(x = 100, y = 50 + index*20)

            self.arithmetic_botton[dir] = entities.Button(self, self.operation_tabs['Arithmetic'],'arithmetic_scale',['1','pi','2pi'],width = 3)
            self.arithmetic_botton[dir].place(x = 120, y = 50 + index*20)

        mult_calc = tk.ttk.Button(self.operation_tabs['Arithmetic'], text="multiply", command = self.multiply)
        mult_calc.place(x = 10, y = 10)

        mult_calc = tk.ttk.Button(self.operation_tabs['Arithmetic'], text="divide", command = self.divide)
        mult_calc.place(x = 150, y = 10)

    def multiply(self):
        for index, dir in enumerate(self.arithmetic.keys()):
            scale = np.pi*int(self.arithmetic_botton[dir].index) #0 -> 0, 1 -> pi, 2 -> 2pi
            scale = max(scale,1)#if 0, make it 1
            value = float(self.arithmetic[dir].get())
            self.overview.figure_handeler.figures['center'].data[index] *= (value/scale)
        self.overview.figure_handeler.draw()

    def divide(self):
        for index, dir in enumerate(self.arithmetic.keys()):
            scale = np.pi*int(self.arithmetic_botton[dir].index) #0 -> 0, 1 -> pi, 2 -> 2pi
            scale = max(scale,1)#if 0, make it 1
            value = float(self.arithmetic[dir].get())
            self.overview.figure_handeler.figures['center'].data[index] /= (value/scale)
        self.overview.figure_handeler.draw()

    #clipbo
    def define_c_clip(self):
        mult_calc = tk.ttk.Button(self.operation_tabs['Clip'], text="circle clip", command = self.overview.figure_handeler.make_circle)
        mult_calc.place(x = 0, y = 10)

        self.c_clip_entry = tk.ttk.Entry(self.operation_tabs['Clip'], width= 3)#
        default = self.overview.data_handler.file.save_dict.get('c_clip_entry','17')
        self.c_clip_entry.insert(0, default)#default text
        self.c_clip_entry.place(x = 110, y = 10)
