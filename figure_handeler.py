import figure, processing

class Figure_handeler():
    def __init__(self,data_tab):
        self.data_tab = data_tab
        self.pos = [0,0]#posirion of the main figure
        self.size = [445,430]#figure canvas size
        self.make_figures()

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

    def redraw(self):
        for figure in self.figures.values():
            figure.redraw()

    def update_colour_scale(self,value):
        for figure in self.figures.values():
            self.redraw()

    #methods
    def k_convert(self):#called when pressed the botton
        adjust = processing.Convert_k(self.figures['center'])
        adjust.run()

class Threedimension(Figure_handeler):#fermi surface
    def __init__(self,data_tab):
        super().__init__(data_tab)

    def make_figures(self):
        figures = {'center':figure.FS,'right':figure.Band_right,'down':figure.Band_down,'corner':figure.DOS_right_down}
        positions = {'center':[self.pos[0],self.pos[1]],'right':[self.pos[0]+self.size[0],self.pos[1]],'down':[self.pos[0],self.pos[1]+self.size[1]],'corner':[self.pos[0]+self.size[0],self.pos[1]+self.size[1]]}
        self.figures = {}
        for key in figures.keys():
            self.figures[key] = figures[key](self,positions[key])

    def fermi_level(self):#called when pressed the botton
        adjust = processing.Fermi_level_FS(self.figures['center'])
        adjust.run()

    def kz_convert(self):#called when pressed the botton
        adjust = processing.Convert_kz(self.figures['center'])
        adjust.run()

class Twodimension(Figure_handeler):#band
    def __init__(self,data_tab):
        super().__init__(data_tab)

    def make_figures(self):
        figures = {'center':figure.Band,'right':figure.DOS_right,'down':figure.DOS_down}
        positions = {'center':[self.pos[0],self.pos[1]],'right':[self.pos[0]+self.size[0],self.pos[1]],'down':[self.pos[0],self.pos[1]+self.size[1]]}
        self.figures = {}
        for key in figures.keys():
            self.figures[key] = figures[key](self,positions[key])#make a class based on the name of the newstate: need to import sys

    def fermi_level(self):#called when pressed the botton
        adjust = processing.Fermi_level_band(self.figures['center'])
        adjust.run()

    def kz_convert(self):#called when pressed the botton
        pass
