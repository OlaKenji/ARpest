import figure, processing, constants
import numpy as np

class Figure_handeler():
    def __init__(self,data_tab):
        self.data_tab = data_tab#overview
        self.pos = constants.figure_position#posirion of the main figure
        self.size = constants.figure_grid#figure canvas size
        self.make_figures()
        self.colour_bar = figure.Colour_bar(self)

    def update_intensity(self):#called after k convert or fermi adjust
        for key in self.figures.keys():
            if key == 'center': continue
            self.figures[key].intensity()

    def update_sort_data(self):#called after k convert or fermi adjust
        for key in self.figures.keys():
            if key == 'center': continue
            self.figures[key].sort_data()

    def update_mouse_range(self):#called after k convert or fermi adjust
        for figure in self.figures.values():
            figure.mouse_range()#update the x,y limits

    def update_line_width(self):
        for figure in self.figures.values():
            figure.cursor.update_line_width()

    def draw(self):
        for figure in self.figures.values():
            figure.draw()

    def redraw(self,*arg):#called from overview (init), colour scale slide,
        for figure in self.figures.values():
            figure.redraw()

    #methods
    def k_convert(self):#called when pressed the botton
        adjust = processing.Convert_k(self.figures['center'])
        adjust.run()

    def symmetrise(self):#called when pressed the botton
        pass

    def derivative(self):#called when pushing the 2nd derivative botton
        if self.data_tab.operations.orientation_botton.configure('text')[-1] == 'horizontal':
            adjust = processing.Derivative_x(self.figures['center'])
        else:#vertical
            adjust = processing.Derivative_y(self.figures['center'])
        adjust.run()
        self.draw()

    def curvature(self):#called when pushing the 2nd derivative botton
        if self.data_tab.operations.orientation_botton.configure('text')[-1] == 'horizontal':
            adjust = processing.Curvature_x(self.figures['center'])
        else:#vertical
            adjust = processing.Curvature_y(self.figures['center'])
        adjust.run()
        self.draw()

    def reset(self):#the reset bottom -> need to also set the original axes
        self.figures['center'].int = self.figures['center'].original_int
        self.figures['center'].update_colour_scale()
        self.draw()

    def smooth(self):#the smooth botton
        if self.data_tab.operations.orientation_botton.configure('text')[-1] == 'horizontal':
            adjust = processing.Smooth_x(self.figures['center'])
        else:
            adjust = processing.Smooth_y(self.figures['center'])
        adjust.run()
        self.draw()

    def save(self):
        self.figures['center'].save()

    def update_colour_scale(self,value = 0):#called from slider
        value = self.data_tab.operations.color_scale.get()#value of the colour scale
        vmax = self.colour_bar.vlim[1]*float(value)/100
        self.colour_bar.vlim_set = [self.colour_bar.vlim[0],vmax]#for the pop up window -> should just be called once
        self.data_tab.operations.label3.configure(text = (round(float(value),1)))#update the number next to int range slide -> should just be called once

        for figure in self.twoD:#update the 2D figures
            self.figures[figure].update_colour_scale()
        self.colour_bar.update()
        self.redraw()

    def make_grid(self):#called from botton
        self.figures['center'].grid = not self.figures['center'].grid#this shoudl only be called when pressing the botton....
        self.figures['center'].make_grid(self.figures['center'].ax)

    def subtract_BG(self):
        self.figures['center'].subtract_BG()

class Threedimension(Figure_handeler):#fermi surface
    def __init__(self,data_tab):
        super().__init__(data_tab)
        self.twoD = ['center','right','down']

        for fig in self.twoD:#update the 2D figures
            self.figures[fig].update_colour_scale()

    def make_figures(self):
        figures = {'center':figure.FS,'right':figure.Band_right,'down':figure.Band_down,'corner':figure.DOS_right_down}
        positions = {'center':[self.pos[0],self.pos[1]],'right':[self.pos[0]+self.size[0],self.pos[1]],'down':[self.pos[0],self.pos[1]+self.size[1]],'corner':[self.pos[0]+self.size[0],self.pos[1]+self.size[1]]}
        self.figures = {}
        for key in figures.keys():
            self.figures[key] = figures[key](self,positions[key])#figures are initated here

    def fermi_level(self):#called when pressed the botton
        adjust = processing.Fermi_level_FS(self.figures['center'])
        adjust.run()

    def kz_convert(self):#called when pressed the botton
        adjust = processing.Convert_kz(self.figures['center'])
        adjust.run()

    def normalise(self):
        temp = np.transpose(self.figures['center'].data[3],(2, 0, 1))
        for index, ary in enumerate(temp):#divide each angle with maximum
            self.figures['center'].data[3][:,:,index] =  100000000*len(ary)*ary/np.sum(ary)#need to multiply woth large number to compensate for the fact that it becomes int, and not float
        self.figures['center'].intensity()#updayte the intensoty
        self.update_intensity()#updayte the intensoty
        self.colour_bar.update()#update colour bar
        self.draw()#update self.graph

    def integrate(self):
        pass

class Twodimension(Figure_handeler):#band
    def __init__(self,data_tab):
        super().__init__(data_tab)
        self.twoD = ['center']

        for fig in self.twoD:#update the 2D figures
            self.figures[fig].update_colour_scale()

    def make_figures(self):
        figures = {'center':figure.Band,'right':figure.DOS_right,'down':figure.DOS_down}
        positions = {'center':[self.pos[0],self.pos[1]],'right':[self.pos[0]+self.size[0],self.pos[1]],'down':[self.pos[0],self.pos[1]+self.size[1]]}
        self.figures = {}
        for key in figures.keys():
            self.figures[key] = figures[key](self,positions[key])#figures are initated here

    def fermi_level(self):#called when pressed the botton
        adjust = processing.Fermi_level_band(self.figures['center'])
        adjust.run()

    def kz_convert(self):#called when pressed the botton -> can be diabled if it is 2D?
        pass

    def symmetrise(self):#called when pressed the botton
        adjust = processing.Symmetrise(self.figures['center'])
        adjust.run()

    def normalise(self):
        pass

    def integrate(self):
        self.figures['right'].integrate()
        self.figures['down'].integrate()
        self.redraw()
