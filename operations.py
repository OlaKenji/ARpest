import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.colors

import entities

class Operations():
    def __init__(self, overview):
        self.overview = overview
        self.make_box()

        #general
        self.define_dropdowns()
        self.define_int_range()
        self.define_vlim()
        self.define_set_vlim()
        self.define_grid()
        self.define_colour_scale()

        #operations
        self.define_fermilevel()
        self.define_kz()
        self.define_subtract_by()
        self.define_k_convert()
        self.define_symmetrise()
        self.define_derivative()
        self.define_smooth()
        self.define_curvature()
        self.define_normalise_slices()
        self.define_orientation_botton()
        self.define_integrate()
        self.define_EF_correction()
        self.define_divide_by()
        self.define_normalise_cuts()

        #cursor
        self.define_crusorslope()
        self.define_crusor_reset_position()
        self.define_cursor_set_position()

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
        self.define_hori_clip()
        self.define_remove_line()

    def make_box(self):#make a box with operations options on the figures
        self.notebook = tk.ttk.Notebook(master=self.overview.tab,width=610, height=300)#to make tabs
        self.notebook.place(x = 890, y = 80)
        operations = ['General','Operations','Cursor','Figures','Arithmetic','Clip']
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
        self.color_scale = tk.ttk.Scale(self.operation_tabs['General'],from_=0,to=100,orient='horizontal',command = self.overview.figure_handeler.update_colour_scale,value = self.overview.data_handler.save_dict.get('colour_scale',100))#
        self.color_scale.place(x = 0, y = 100)
        label=ttk.Label(self.operation_tabs['General'],text='colour scale',background='white',foreground='black')
        label.place(x = 0, y = 80)
        self.label3 = ttk.Label(self.operation_tabs['General'],text = round(self.overview.data_handler.save_dict.get('colour_scale',100),1),background='white',foreground='black')#need to save it to updat the number next to the slide
        self.label3.place(x = 100, y = 100)

    def define_dropdowns(self):
        commands = ['RdYlBu_r','RdBu_r','terrain','binary', 'binary_r', 'mine'] + sorted(['Spectral_r','bwr','coolwarm', 'twilight_shifted','twilight_shifted_r', 'PiYG', 'gist_ncar','gist_ncar_r', 'gist_stern','gnuplot2', 'hsv', 'hsv_r', 'magma', 'magma_r', 'seismic', 'seismic_r','turbo', 'turbo_r'])
        dropvar = tk.StringVar(self.operation_tabs['General'])
        dropvar.set('colours')
        drop = tk.OptionMenu(self.operation_tabs['General'],dropvar,*commands,command = self.select_drop)
        drop.config(bg="white")
        drop.place(x = 0, y = 0)

    def select_drop(self,event):
        if event == 'mine':
            target_colors = [
                (0.19215686274509805, 0.21176470588235294, 0.5843137254901961, 1.0),
                (0.28865820838139183, 0.48035371011149564, 0.7170319108035371, 1.0),
                (0.4971933871587852, 0.7122645136485968, 0.8380622837370243, 1.0),
                (0.7398692810457518, 0.884967320261438, 0.9333333333333333, 1.0),
                (0.9308727412533642, 0.9732410611303345, 0.8761245674740483, 1.0),
                (0.9977700884275279, 0.930872741253364, 0.6442137639369473, 1.0),
                (0.9934640522875817, 0.7477124183006536, 0.4418300653594771, 1.0),
                (0.9637831603229527, 0.47743175701653207, 0.28581314878892733, 1.0),
                (0.8542868127643214, 0.2116878123798539, 0.1637062668204537, 1.0),
                (0.6470588235294118, 0.0, 0.14901960784313725, 1.0)]
            cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", target_colors)
        else:
            cmap = event

        self.overview.figure_handeler.cmap = cmap
        self.overview.figure_handeler.draw()
        self.overview.figure_handeler.colour_bar.update()

    def define_vlim(self):
        self.vlim_entry = tk.ttk.Entry(self.operation_tabs['General'], width= 10)#
        default = self.overview.data_handler.save_dict.get('vlim','None,None')
        self.vlim_entry.insert(0, default)#default text
        self.vlim_entry.place(x = 150, y = 100)
        label = ttk.Label(self.operation_tabs['General'],text = 'colour limits',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 150, y = 80)

    def define_set_vlim(self):
        button = tk.ttk.Button(self.operation_tabs['General'], text="set colour limit", command = self.overview.figure_handeler.colour_bar.set_vlim,style='soft.TButton')
        button.place(x = 250, y = 100)

    def define_grid(self):
        self.grid_button = entities.Button(self, self.operation_tabs['General'],'grid_button',['grid on','grid off'], command = self.overview.figure_handeler.make_grid)
        self.grid_button.place(x = 150, y = 50)

    #cursor
    def define_crusorslope(self):
        scale = tk.ttk.Scale(self.operation_tabs['Cursor'],from_=-45,to=45,orient='horizontal',command = self.overview.figure_handeler.figures['center'].cursor.update_slope,style="TScale")#
        scale.place(x = 0, y = 150)
        label=ttk.Label(self.operation_tabs['Cursor'],text='slope',background='white',foreground='black')
        label.place(x = 0, y = 130)
        self.label2 = ttk.Label(self.operation_tabs['Cursor'],text = str(0),background='white',foreground='black')#need to save it to updat the number next to the slide
        self.label2.place(x = 100, y = 150)

    def define_crusor_reset_position(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Cursor'], text="reset position", command = self.overview.figure_handeler.figures['center'].cursor.reset_position)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 250)

    def define_cursor_set_position(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Cursor'], text="set position", command = self.overview.figure_handeler.figures['center'].cursor.set_position)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 50)

        self.cursor_position_entry = []
        texts = ['x','y']
        self.cursor_labels = []
        for i in range(0,2):
            self.cursor_position_entry.append(tk.ttk.Entry(self.operation_tabs['Cursor'], width= 5))
            default = self.overview.data_handler.save_dict.get('cursor_position_entry','None')
            self.cursor_position_entry[-1].insert(0, default)#default text
            self.cursor_position_entry[-1].place(x = 0, y = 20 * i)

            label1 = ttk.Label(self.operation_tabs['Cursor'],text = texts[i],background='white',foreground='black')#need to save it to updat the number next to the slide
            label1.place(x = 55, y = 20 * i)

            self.cursor_labels.append(ttk.Label(self.operation_tabs['Cursor'],text = texts[i],background='white',foreground='black'))#need to save it to updat the number next to the slide
            self.cursor_labels[-1].place(x = 70, y = 20 * i)

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

    def define_subtract_by(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Subtract by", command = self.overview.figure_handeler.subtract_by)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 0)
        self.BG_orientation = entities.Button(self, self.operation_tabs['Operations'],'BG_orientation',['...','EDC','MDC','bg Matt'])
        self.BG_orientation.place(x = 120, y = 0)

    def define_divide_by(self):#
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Divide by", command = self.overview.figure_handeler.divide_by)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 30)
        self.divide_by = entities.Button(self, self.operation_tabs['Operations'],'Divide_by',['...','EDC','MDC'])
        self.divide_by.place(x = 120, y = 30)

    def define_fermilevel(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Fermi level ...", command = self.overview.figure_handeler.fermi_level)
        button_calc.place(x = 0, y = 70)
        self.fermi_normalisation = entities.Button(self, self.operation_tabs['Operations'],'Fermi_level',['on','off'])
        self.fermi_normalisation.place(x = 120, y = 70)

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
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="integrate", command = self.overview.figure_handeler.integrate,style='soft.TButton')#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 190)

    def define_EF_correction(self):
        botton = tk.ttk.Button(self.operation_tabs['Operations'], text="EF corr", command = self.overview.figure_handeler.EF_corr)#which figures shoudl have access to this?
        botton.place(x = 0, y = 250)

    def define_normalise_slices(self):#for e.g. kz
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Normalise slices", command = self.overview.figure_handeler.normalise_slices)#which figures shoudl have access to this?
        button_calc.place(x = 0, y = 220)

    def define_normalise_cuts(self):
        button_calc = tk.ttk.Button(self.operation_tabs['Operations'], text="Normalise cuts", command = self.overview.figure_handeler.normalise_cuts,style='soft.TButton')#which figures shoudl have access to this?
        button_calc.place(x = 120, y = 190)

    #figure tab
    def define_fig_size(self):
        self.fig_size_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 10)#
        default = self.overview.data_handler.save_dict.get('fig_size_entry','3.3,3.3')
        self.fig_size_entry.insert(0, default)#default text
        self.fig_size_entry.place(x = 0, y = 50)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'figure size',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 50)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_fig_size,style='soft.TButton')#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 50)

    def define_fig_lim(self):
        self.fig_lim_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 20)#
        default = self.overview.data_handler.save_dict.get('fig_lim_entry','None,None;None,None')
        self.fig_lim_entry.insert(0, default)#default text
        self.fig_lim_entry.place(x = 0, y = 80)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'figure limits',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 80)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_fig_lim,style='soft.TButton')#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 80)

    def define_fig_label(self):
        self.fig_label_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 10)#
        default = self.overview.data_handler.save_dict.get('fig_label_entry','x,y')
        self.fig_label_entry.insert(0, default)#default text
        self.fig_label_entry.place(x = 0, y = 110)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'figure label',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 110)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_fig_label,style='soft.TButton')#which figures shoudl have access to this?
        button_calc.place(x = 300, y = 110)

        self.define_label_size()

    def define_label_size(self):
        self.fig_label_size_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 5)#
        default = self.overview.data_handler.save_dict.get('fig_label_size_entry','10,10')
        self.fig_label_size_entry.insert(0, default)#default text
        self.fig_label_size_entry.place(x = 135, y = 110)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'size',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 100, y = 110)

    def define_colourbar_size(self):
        self.colourbar_size_entry = tk.ttk.Entry(self.operation_tabs['Figures'], width= 10)#
        default = self.overview.data_handler.save_dict.get('colorbar_size_entry','3.3,0.7')
        self.colourbar_size_entry.insert(0, default)#default text
        self.colourbar_size_entry.place(x = 0, y = 200)
        label = ttk.Label(self.operation_tabs['Figures'],text = 'colourbar size',background='white',foreground='black')#need to save it to updat the number next to the slide
        label.place(x = 200, y = 200)

        button_calc = tk.ttk.Button(self.operation_tabs['Figures'], text="reset", command = self.reset_colorbar_size,style='soft.TButton')#which figures shoudl have access to this?
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

            default = self.overview.data_handler.save_dict.get('fig_margines',{'top':0.93,'left':0.18,'right':0.97,'bottom':0.13})
            self.fig_margines[margin].insert(0, default[margin])#default text
            self.fig_margines[margin].place(x = 50 + 50*index, y = 20)
            label = ttk.Label(self.operation_tabs['Figures'],text = margin,background='white',foreground='black')#need to save it to updat the number next to the slide
            label.place(x = 50 + 50*index, y = 0)

            default = self.overview.data_handler.save_dict.get('colourbar_margines',{'top':0.9,'left':0.03,'right':0.96,'bottom':0.7})
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

        self.fig_label_size_entry.delete(0, "end")
        self.fig_label_size_entry.insert(0, '12,12')#default text

    #Arithmetic
    def define_multiply(self):
        self.arithmetic = {'x':None,'y':None}
        self.arithmetic_botton = {'x':None,'y':None}
        for index, dir in enumerate(self.arithmetic.keys()):
            self.arithmetic[dir] = tk.ttk.Entry(self.operation_tabs['Arithmetic'], width= 10)#
            default = self.overview.data_handler.save_dict.get('arithmetic_' + dir,'1')
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

        mult_calc = tk.ttk.Button(self.operation_tabs['Arithmetic'], text="subtract", command = self.subtract)
        mult_calc.place(x = 290, y = 10)

        mult_calc = tk.ttk.Button(self.operation_tabs['Arithmetic'], text="scale", command = self.scale)
        mult_calc.place(x = 10, y = 200)   
        self.intensity_scale = tk.ttk.Entry(self.operation_tabs['Arithmetic'], width= 10)#
        self.intensity_scale.insert(1, 1)#default text
        self.intensity_scale.place(x = 10, y = 250)

    def multiply(self):
        dict = self.overview.data_handler.file.data[-1].copy()
        name = ''
        symbol = ['1','pi','2pi']
        for index, dir in enumerate(self.arithmetic.keys()):#for x and y
            scale = np.pi*int(self.arithmetic_botton[dir].index) #0 -> 0, 1 -> pi, 2 -> 2pi
            scale = max(scale,1)#if 0, make it 1
            value = float(self.arithmetic[dir].get())

            dict[dir+'scale'] = dict[dir+'scale'] * (value/scale)
            name += dir + '=' + str(value) + '/' + symbol[int(self.arithmetic_botton[dir].index)] + '\ '

        self.overview.data_handler.state_catalog.add_state(dict,'multiplied\ by:\ ' + name)

    def divide(self):
        dict = self.overview.data_handler.file.data[-1].copy()
        name = ''
        symbol = ['1','pi','2pi']
        for index, dir in enumerate(self.arithmetic.keys()):#for x and y
            scale = np.pi*int(self.arithmetic_botton[dir].index) #0 -> 0, 1 -> pi, 2 -> 2pi
            scale = max(scale,1)#if 0, make it 1
            value = float(self.arithmetic[dir].get())

            dict[dir+'scale'] = dict[dir+'scale'] / (value/scale)
            name += dir + '=' + str(value) + '/' + symbol[int(self.arithmetic_botton[dir].index)] + '\ '

        self.overview.data_handler.state_catalog.add_state(dict,'divided\ by:\ ' + name)

    def subtract(self):
        dict = self.overview.data_handler.file.data[self.overview.data_handler.index].copy()
        name = ''
        symbol = ['1','pi','2pi']
        for index, dir in enumerate(self.arithmetic.keys()):#for x and y
            scale = np.pi*int(self.arithmetic_botton[dir].index) #0 -> 0, 1 -> pi, 2 -> 2pi
            scale = max(scale,1)#if 0, make it 1
            value = float(self.arithmetic[dir].get())

            dict[dir+'scale'] = dict[dir+'scale'] - (value/scale)
            name += dir + '=' + str(value) + '/' + symbol[int(self.arithmetic_botton[dir].index)] + '\ '

        self.overview.data_handler.state_catalog.add_state(dict,'subtracted\ by:\ ' + name)

    def scale(self):
        dict = self.overview.data_handler.file.data[-1].copy()
        scale = float(self.intensity_scale.get())
        dict['data'] = dict['data']/ scale
        self.overview.data_handler.state_catalog.add_state(dict,'scaled\ by:\ ' + self.intensity_scale.get())

    #clip
    def define_c_clip(self):
        mult_calc = tk.ttk.Button(self.operation_tabs['Clip'], text="circle clip", command = self.overview.figure_handeler.make_circle)
        mult_calc.place(x = 0, y = 10)

        self.c_clip_entry = tk.ttk.Entry(self.operation_tabs['Clip'], width= 3)#
        default = self.overview.data_handler.save_dict.get('c_clip_entry','17')
        self.c_clip_entry.insert(0, default)#default text
        self.c_clip_entry.place(x = 110, y = 10)

    def define_hori_clip(self):
        mult_calc = tk.ttk.Button(self.operation_tabs['Clip'], text="hori clip", command = self.overview.figure_handeler.make_hori_clip)
        mult_calc.place(x = 0, y = 40)
        self.hori_clip_enties = []
        default_values = [-15,15]
        for i in range(0,2):
            self.hori_clip_enties.append(tk.ttk.Entry(self.operation_tabs['Clip'], width= 3))
            default = self.overview.data_handler.save_dict.get('hori_clip_enties',str(default_values[i]))
            self.hori_clip_enties[i].insert(0, default)#default text
            self.hori_clip_enties[i].place(x = 110 + 40*i, y = 40)

    def define_remove_line(self):
        pass
