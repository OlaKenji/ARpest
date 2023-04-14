class Auto_cursor():
    def __init__(self, figure):
        self.figure = figure

        self.text = self.figure.ax.text(0.5, 1, '', zorder=4,transform = self.figure.ax.transAxes,horizontalalignment='center',verticalalignment='top')
        self.figure.ax.add_artist(self.text)

        self.xlimits = self.figure.xlimits
        self.ylimits = self.figure.ylimits

        self.pos = [(self.xlimits[0]+self.xlimits[-1])/2,(self.ylimits[0]+self.ylimits[-1])/2]

        thickness=self.figure.sub_tab.int_range+0.8
        self.dyn_horizontal_line = self.figure.ax.axhline(self.pos[1],color='k', lw=thickness, ls='--',zorder=3)
        self.dyn_vertical_line = self.figure.ax.axvline(self.pos[0],color='k', lw=thickness, ls='--',zorder=3)

        self.sta_horizontal_line = self.figure.ax.axhline(self.pos[1],color='r', lw=thickness,zorder=2)
        self.sta_vertical_line = self.figure.ax.axvline(self.pos[0],color='r', lw=thickness,zorder=2)

    def draw_sta_line(self):
        thickness=self.figure.sub_tab.int_range+0.8
        self.sta_horizontal_line = self.figure.ax.axhline(self.pos[1],color='r', lw=thickness,zorder=2)
        self.sta_vertical_line = self.figure.ax.axvline(self.pos[0],color='r', lw=thickness,zorder=2)
        self.redraw()

    def update_event(self,event):
        self.xlimits = self.figure.xlimits
        self.ylimits = self.figure.ylimits
        scalex = event.x/self.figure.size[0]
        scaley = event.y/self.figure.size[1]
        return [scalex*(self.xlimits[1]-self.xlimits[0])+self.xlimits[0],scaley*(self.ylimits[0]-self.ylimits[1])+self.ylimits[1]]

    def redraw(self):
        self.figure.canvas.restore_region(self.figure.curr_background)
        self.figure.ax.draw_artist(self.text)
        self.figure.ax.draw_artist(self.dyn_horizontal_line)
        self.figure.ax.draw_artist(self.dyn_vertical_line)
        self.figure.ax.draw_artist(self.sta_horizontal_line)
        self.figure.ax.draw_artist(self.sta_vertical_line)
        #self.figure.range_cursor.redraw()
        self.figure.canvas.blit(self.figure.ax.bbox)

    def on_mouse_move(self, event):
        pos = self.update_event(event)
        self.dyn_horizontal_line.set_ydata(pos[1])
        self.dyn_vertical_line.set_xdata(pos[0])
        self.text.set_text('x=%1.2f, y=%1.2f' % (pos[0], pos[1]))
        self.redraw()

    def on_mouse_click(self,event):
        self.pos = self.update_event(event)
        self.sta_horizontal_line.set_ydata(self.pos[1])
        self.sta_vertical_line.set_xdata(self.pos[0])
        self.figure.click(self.pos)

class Range_cursor():
    def __init__(self, figure):
        self.figure = figure

        self.text = self.figure.ax.text(0.5, 1, '', zorder=4,transform = self.figure.ax.transAxes,horizontalalignment='center',verticalalignment='top')
        self.figure.ax.add_artist(self.text)

        self.xlimits = self.figure.xlimits
        self.ylimits = self.figure.ylimits

        self.pos = self.figure.cursor.pos[1]

        self.width=self.figure.sub_tab.range
        thickness = self.figure.sub_tab.int_range + 0.8
        self.up_line = self.figure.ax.axhline(self.pos+self.width,color='y', lw=thickness)
        self.down_line = self.figure.ax.axhline(self.pos-self.width,color='y', lw=thickness)

    def draw_sta_line(self):
        self.width=self.figure.sub_tab.range
        thickness=self.figure.sub_tab.int_range + 0.8

        self.up_line = self.figure.ax.axhline(self.pos+self.width,color='y', lw=thickness)
        self.down_line = self.figure.ax.axhline(self.pos-self.width,color='y', lw=thickness)
        self.redraw()

    def on_mouse_move(self, pos):
        self.redraw()

    def redraw(self):
        self.figure.canvas.restore_region(self.figure.curr_background)
        self.figure.ax.draw_artist(self.text)
        self.figure.ax.draw_artist(self.up_line)
        self.figure.ax.draw_artist(self.down_line)
        self.figure.canvas.blit(self.figure.ax.bbox)

    def update_event(self,event):
        scalex = event.x/self.figure.size[0]
        scaley = event.y/self.figure.size[1]
        return scaley*(self.ylimits[0]-self.ylimits[1])+self.ylimits[1]#[scalex*(self.xlimits[1]-self.xlimits[0])+self.xlimits[0],scaley*(self.ylimits[0]-self.ylimits[1])+self.ylimits[1]]

    def drag(self,event):
        self.pos = self.update_event(event)
        self.up_line.set_ydata(self.pos+self.width)
        self.down_line.set_ydata(self.pos-+self.width)
        self.redraw()

    def get_position(self):
        return [self.pos-self.width,self.pos+self.width]

class Verti_cursor():#not in use
    def __init__(self, figure):
        self.figure = figure
        self.ax = self.figure.ax

        self.text = self.ax.text(0.5, 1, '', zorder=4,transform = self.ax.transAxes,horizontalalignment='center',verticalalignment='top')
        self.ax.add_artist(self.text)

        x = self.figure.center.cursor.pos[0]

        self.dyn_line = self.ax.axvline(x,color='k', lw=0.8, ls='--')
        self.sta_line = self.ax.axvline(x,color='r', lw=0.8)

    def on_mouse_move(self, pos):
        self.dyn_line.set_xdata(pos[0])
        self.text.set_text('x=%1.2f, y=%1.2f' % (pos[0], pos[1]))
        self.figure.redraw()

    def redraw(self):
        self.ax.draw_artist(self.text)
        self.ax.draw_artist(self.dyn_line)
        self.ax.draw_artist(self.sta_line)

    def on_mouse_click(self,pos):
        self.sta_line.set_xdata(pos[0])
        self.figure.redraw()
