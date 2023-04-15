import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import tkinter as tk
import numpy as np
import json

import processing, cursor, states_figure

class Functions():#figure functionality not being used
    def __init__(self):
        pass

    def subtract_BG(self):#the BG botton calls it
        pass

    #not in use
    def define_normalise(self):
        self.define_norm_entry()
        button_calc = tk.Button(self.sub_tab.tab, text="Normalise", command = self.normalise)
        offset = [200,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def define_norm_entry(self):
        self.e1 = tk.Entry(self.sub_tab.tab,width=2)#the step size
        offset = [300,0]
        self.e1.place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])
        self.e1.insert(0, 1)#default value 1

    def normalise(self):
        norm = float(self.e1.get())
        self.int = self.int/norm
        self.draw()

class Figure(Functions):
    def __init__(self,sub_tab,pos):
        self.sub_tab = sub_tab#analysis or overview
        self.pos = pos
        self.label = ['x','y']
        self.intensity()
        self.sort_data()
        self.original_int = self.int

        #self.colour_limit()
        self.define_canvas()
        self.define_mouse()
        self.define_dropdowns()

        self.state = states_figure.Raw(self)
        self.data_processes = {'Raw':processing.Raw,'Derivative_x':processing.Derivative_x,'Derivative_y':processing.Derivative_y,'Convert_k':processing.Convert_k,'Range_plot':processing.Range_plot}
        self.set_method('Raw')
        #self.define_normalise()
        self.define_export()
        self.define_fermilevel()

    def set_method(self,method):
        self.data_processor = self.data_processes[method](self)

    def define_canvas(self):
        self.fig = plt.Figure(figsize = (4.45,4.3))
        self.size = self.fig.get_size_inches()*self.fig.dpi
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(top=0.93,left=0.15,right=0.97)
        self.canvas = FigureCanvasTkAgg(self.fig, master = self.sub_tab.tab)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)

        offset = [0,0]
        self.canvas.get_tk_widget().place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])#grid(row=1,column=self.column)

    def define_mouse(self):#called in init and from processing
        self.xlimits = [np.array(self.data[0]).min(), np.array(self.data[0]).max()]#used for crusor
        self.ylimits = [np.array(self.data[1]).min(), np.array(self.data[1]).max()]
        self.cursor = cursor.Auto_cursor(self)

        self.canvas.get_tk_widget().bind( "<Motion>", self.cursor.on_mouse_move)
        self.canvas.get_tk_widget().bind( "<Button-1>", self.cursor.on_mouse_click)#left click
        self.canvas.get_tk_widget().bind( "<Button-2>", self.right_click)#right click
        self.canvas.get_tk_widget().bind( "<Double-Button-1>", self.double_click)#double click

    def define_dropdowns(self):
        commands = ['Raw','Derivative_x','Derivative_y','Convert_k']
        if str(type(self.sub_tab).__name__) == 'Analysis':#on analysis tab
            commands.append('Range_plot')

        dropvar = tk.StringVar()
        dropvar.set(commands[0])
        drop = tk.OptionMenu(self.sub_tab.tab,dropvar,*commands,command = self.select_drop)
        offset=[50,0]
        drop.place(x = self.pos[0] + offset[0], y = self.pos[1] + offset[1])

    def select_drop(self,event):
        self.data_processor.exit()#exit the old one
        self.set_method(event)#point to new method and make the object
        self.data_processor.run()#run the thing
        self.draw()

    def double_click(self,event):
        pos = [self.sub_tab.center.pos[0],self.sub_tab.center.pos[1]]
        new_fig = type(self)#make a new figure
        self.sub_tab.data_tab.append_tab(new_fig,pos,self.int)

    def click(self,pos):
        self.cursor.redraw()

    def right_click(self,event):
        self.sub_tab.data_tab.gui.pop_up()#call gui to make a new window object
        self.plot(self.sub_tab.data_tab.gui.pop.ax)#plot the fraph onto the popup ax
        self.sub_tab.data_tab.gui.pop.pop_canvas.draw()#draw it after plot

    def draw(self):
        self.ax.cla()
        self.plot(self.ax)
        self.set_label()
        self.canvas.draw()
        self.curr_background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def redraw(self):
        self.canvas.restore_region(self.curr_background)
        self.ax.draw_artist(self.graph)
        self.canvas.blit(self.ax.bbox)
        self.curr_background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.cursor.redraw()

    def int_range(self,index):
        if self.sub_tab.int_range == 0:#if no integrate
            return index,index+1,1
        else:#if integrate
            if index-self.sub_tab.int_range < 0:
                index=self.sub_tab.int_range
            start = index-self.sub_tab.int_range
            stop = index+self.sub_tab.int_range+1
            step = stop - start
            return start,stop,step

    def define_export(self):
        button_calc = tk.Button(self.sub_tab.tab, text="Export", command = self.export)
        offset = [340,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def export(self):
        export_data = {'x':self.data[0].tolist(), 'y':self.data[1].tolist(), 'z':self.int.tolist()}
        path = self.sub_tab.data_tab.gui.start_path + '/' + self.sub_tab.data_tab.name
        with open(path+"_exported.json", "w") as outfile:
            json.dump(export_data, outfile)

    def set_label(self):
        self.ax.set_xlabel(self.label[0])
        self.ax.set_ylabel(self.label[1])

    def colour_limit(self):#called in init
        self.vmin = self.int.min()
        self.vmax = self.int.max()

    def gold(self):#sort the data: called from fermi_level processing init
        pass#self.data[0] is assumed to be kinetic energy need to transpose back and forth if this is not the case (not implemented)

    def define_fermilevel(self):
        button_calc = tk.Button(self.sub_tab.tab, text="Fermi level", command = self.fermi_level)
        offset = [200,0]
        button_calc.place(x = self.pos[0]+offset[0], y = self.pos[1]+offset[1])

    def fermi_level(self):
        adjust = processing.Fermi_level(self)
        adjust.run()

class FS(Figure):
    def __init__(self,data_tab,pos):
        super().__init__(data_tab,pos)
        self.label = ['x angle','y angle']
        self.right = Band_right(self,[self.pos[0]+self.size[0],self.pos[1]])
        self.down = Band_down(self,[self.pos[0],self.pos[1]+self.size[1]])
        self.right_down = DOS_right_down(self,[self.pos[0]+self.size[0],self.pos[1]+self.size[1]])
        self.draw()

    def plot(self,ax = None):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int, zorder=1,cmap=self.sub_tab.cmap)#FS,norm = colors.Normalize(vmin=self.vmin, vmax=self.vmax)
        #self.fig.colorbar(self.graph)

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.xscale,self.sub_tab.data_tab.data.yscale,self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0]-pos[0])
        index1 = difference_array.argmin()
        self.right.intensity(index1)
        self.right.tilt = self.sub_tab.data_tab.data.xscale[index1]
        self.right.plot(self.right.ax)
        self.right.redraw()

        difference_array = self.state.difference_array(pos[1])
        index2 = difference_array.argmin()
        self.down.intensity(index2)
        self.down.tilt = self.sub_tab.data_tab.data.yscale[index2]
        self.down.plot(self.down.ax)
        self.down.redraw()

    def intensity(self,z=0):
        start,stop,step=self.int_range(z)
        self.int = sum(self.sub_tab.data_tab.data.data[start:stop:1])/step

    def define_angle2k(self):#called from procssing
        return self.data[1], self.data[0]

    def angle2k(self,kx,ky):#the stuff to convert
        self.data[0] = kx
        self.data[1] = ky
        self.xlimits = [min(self.data[0][0]), max(self.data[0][0])]#used for crusor
        self.ylimits = [min(self.data[1][0]), max(self.data[1][-1])]

    def update_cursor(self):
        self.cursor.update_line_width()
        self.right.cursor.update_line_width()
        self.down.cursor.update_line_width()
        self.right_down.cursor.update_line_width()

    def draw(self):
        super().draw()
        self.right.draw()
        self.down.draw()
        self.right_down.draw()

class Band_right(Figure):
    def __init__(self,center,pos):
        super().__init__(center.sub_tab,pos)
        self.center = center

    def subtract_BG(self):#the BG botton calls it
        difference_array1 = np.absolute(self.data[0] - self.cursor.sta_vertical_line.get_data()[0])
        index1 = difference_array1.argmin()

        bg = np.mean(self.int[:,index1:len(self.data[0])],axis=1)#axis = 0is vertical, axis =1 is horizontal means
        int = self.int.transpose()
        int -=  bg
        self.int = int.transpose()
        self.draw()

    def plot(self,ax=None):#2D plotnp.clip(data['z'],None,3000)
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int, zorder=1,cmap=self.sub_tab.cmap)#FS

    def intensity(self,y=0):
        start,stop,step = self.int_range(y)
        self.int = []
        for ary in self.sub_tab.data_tab.data.data:
            self.int.append(np.sum(ary[:,start:stop:1],axis=1)/step)
        self.int = np.transpose(self.int)

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.zscale,self.sub_tab.data_tab.data.yscale,self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array1 = np.absolute(self.sub_tab.data_tab.data.yscale-pos[1])
        index1 = difference_array1.argmin()

        self.center.right_down.intensity_right(index1)
        self.center.right_down.draw()
        #self.gui.right_down.plot()
        #self.gui.right_down.redraw()

    def define_angle2k(self):#called from procssing
        return self.data[1],np.array([self.tilt])

    def angle2k(self,kx,ky):#the stuff to convert
        #self.data[0] = kx
        self.data[1] = ky
        self.ylimits = [min(self.data[1][0]), max(self.data[1][-1])]

class Band_down(Figure):
    def __init__(self,center,pos):
        super().__init__(center.sub_tab,pos)
        self.center = center

    def subtract_BG(self):#the BG botton calls it
        difference_array1 = np.absolute(self.data[1] - self.cursor.sta_horizontal_line.get_data()[1])
        index1 = difference_array1.argmin()
        bg = np.mean(self.int[index1:len(self.data[1]),:],axis=0)#axis = 0is vertical, axis =1 is horizontal means
        self.int -=  bg
        self.draw()

    def plot(self,ax=None):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int,zorder=1,cmap=self.sub_tab.cmap)#FS

    def intensity(self,y=0):
        start,stop,step=self.int_range(y)
        int = []
        for ary in self.sub_tab.data_tab.data.data:
            int.append(sum(ary[start:stop:1])/step)
        self.int = np.array(int)

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.xscale, self.sub_tab.data_tab.data.zscale,self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array1 = np.absolute(self.sub_tab.data_tab.data.xscale-pos[0])
        index1 = difference_array1.argmin()

        self.center.right_down.intensity_down(index1)
        self.center.right_down.draw()
        #self.gui.right_down.plot()
        #self.gui.right_down.redraw()

    def angle2k(self,kx,ky):#the stuff to convert
        self.data[0] = kx
        #self.data[1] = ky
        self.xlimits = [min(self.data[0][0]), max(self.data[0][0])]#used for crusor

    def define_angle2k(self):#called from procssing
        return np.array([self.tilt]),self.data[0]

class DOS_right_down(Figure):
    def __init__(self,center,pos):
        self.center = center
        super().__init__(center.sub_tab,pos)

    def sort_data(self):
        self.int=(self.int_right+self.int_down)/2
        self.data = [self.sub_tab.data_tab.data.zscale,self.int]

    def intensity(self,idx=0):
        self.intensity_right(idx)
        self.intensity_down(idx)

    def intensity_right(self,idx=0):
        start,stop,step=self.int_range(idx)
        self.int_right = sum(self.center.right.int[start:stop:1])/step

    def intensity_down(self,idx=0):
        start,stop,step=self.int_range(idx)
        self.int_down=[]
        for ary in self.center.down.int:
            self.int_down.append(sum(ary[start:stop:1])/step)

    def plot(self,ax=None):#2D plot
        self.graph1=ax.plot(self.sub_tab.data_tab.data.zscale, self.int_right,zorder=3)[0]
        self.graph2=ax.plot(self.sub_tab.data_tab.data.zscale, self.int_down,zorder=3)[0]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.sub_tab.data_tab.data.zscale-pos[0])
        index1 = difference_array.argmin()
        self.center.intensity(index1)
        self.center.plot(self.center.ax)
        self.center.redraw()

class Band(Figure):
    def __init__(self,data_tab,pos):
        super().__init__(data_tab,pos)
        self.tilt = -3.5#np.array([float(self.sub_tab.data_tab.data.metadata['T'])])
        self.right = DOS_right(self,[self.pos[0]+self.size[0],self.pos[1]])
        self.down = DOS_down(self,[self.pos[0],self.pos[1]+self.size[1]])
        self.draw()

    def subtract_BG(self):#the BG botton calls it
        self.state.bg_subtract()#run the appropriate method
        self.draw()
        self.click([self.cursor.sta_vertical_line.get_data()[0],self.cursor.sta_horizontal_line.get_data()[1]])#update the right and down figures

    def plot(self,ax):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int, zorder=1, cmap = self.sub_tab.cmap)#FS
        #ax.set_ylim(74.7, 75.3)

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.xscale, self.sub_tab.data_tab.data.yscale, self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.data[0] - pos[0])#subtract for each channel, works.
        index1 = self.state.click_right(difference_array)
        self.right.intensity(index1)
        self.right.draw()

        difference_array = np.absolute(self.data[1] - pos[1])
        index2 = self.state.click_down(difference_array)
        self.down.intensity(index2)
        self.down.draw()

    def intensity(self,y = 0):
        self.int = self.sub_tab.data_tab.data.data[0]

    def angle2k(self,kx,ky):#the stuff to convert
        self.data[1] = ky
        self.ylimits = [min(self.data[1][0]), max(self.data[1][-1])]

    def define_angle2k(self):#called from procssing
        return self.data[1],np.array([self.tilt])

    def update_cursor(self):#called when changing the int range
        self.cursor.update_line_width()
        self.right.cursor.update_line_width()
        self.down.cursor.update_line_width()

    def draw(self):
        super().draw()
        self.right.draw()
        self.down.draw()

class DOS_right(Figure):
    def __init__(self,center,pos):
        self.center = center
        super().__init__(center.sub_tab,pos)

    def sort_data(self):
        self.data = [self.int,self.center.data[1]]

    def intensity(self,x = 0):
        start,stop,step=self.int_range(x)
        self.int=[]
        for ary in self.center.int:
            self.int.append(sum(ary[start:stop:1])/step)
    #    self.int=[]
        #for ary in self.sub_tab.center.int:
        #    self.int.append(ary[x])
        self.xlimits = [min(self.int), max(self.int)]

    def plot(self,ax=None):#2D plot
        self.graph = ax.plot(self.int,self.center.data[1])[0]

class DOS_down(Figure):
    def __init__(self,center,pos):
        self.center = center
        super().__init__(center.sub_tab,pos)

    def sort_data(self):
        self.data=[self.center.data[0],self.int]

    def intensity(self,y=0):
        start,stop,step=self.int_range(y)
        self.int = sum(self.center.int[start:stop:1])/step
        #self.int = self.sub_tab.center.int[y]
        self.ylimits = [min(self.int), max(self.int)]

    def plot(self,ax=None):#2D plot
        self.graph = ax.plot(self.data[0], self.int)[0]

class Band_scan(Figure):
    def __init__(self,data_tab,pos):
        super().__init__(data_tab,pos)
        self.define_slide()
        self.right = DOS_right(self,[self.pos[0]+self.size[0],self.pos[1]])
        self.down = DOS_down(self,[self.pos[0],self.pos[1]+self.size[1]])

    def define_slide(self):
        scale = tk.Scale(self.sub_tab.tab,from_=0,to=len(self.sub_tab.data_tab.data.data[0][0][0])-1,orient=tk.HORIZONTAL,label='scan number',command=self.update_range,resolution=1)
        scale.pack()

    def update_range(self,value):
        self.intensity(int(value))
        self.draw()

    def plot(self,ax=None):#2D plot
        self.graph = ax.pcolormesh(self.data[0], self.data[1], self.int,zorder=1,cmap=self.sub_tab.cmap)#FS

    def intensity(self,y = 0):
        #self.int = self.sub_tab.data_tab.data.data[0]
        inss = []
        for int in self.sub_tab.data_tab.data.data[0]:
            for ins in int:
                inss.append(ins[y])

        self.int = np.array(inss).reshape((len(self.sub_tab.data_tab.data.data[0][0]),len(self.sub_tab.data_tab.data.data[0])),order='F')

    def sort_data(self):
        self.data = [self.sub_tab.data_tab.data.yscale, self.sub_tab.data_tab.data.xscale, self.sub_tab.data_tab.data.data]

    def click(self,pos):
        super().click(pos)
        difference_array = np.absolute(self.sub_tab.data_tab.data.xscale-pos[0])
        index1 = difference_array.argmin()
        self.right.intensity(index1)
        self.right.draw()
        #self.right.plot()
        #self.right.redraw()

        difference_array = np.absolute(self.sub_tab.data_tab.data.yscale-pos[1])
        index2 = difference_array.argmin()
        self.down.intensity(index2)
        self.down.draw()
        #self.down.plot()
        #self.down.redraw()

    def draw(self):
        super().draw()
        self.right.draw()
        self.down.draw()
