import math
import matplotlib.pyplot as plt
import numpy as np

class Auto_cursor():
    def __init__(self, figure):
        self.figure = figure
        
        self.text = self.figure.ax.text(0.5, 1, '', zorder=4,transform = self.figure.ax.transAxes,horizontalalignment='center',verticalalignment='top')

        self.center = [(self.figure.xlimits[0]+self.figure.xlimits[-1])*0.5,(self.figure.ylimits[0]+self.figure.ylimits[-1])*0.5]
        self.pos = self.figure.overview.data_handler.save_dict.get(type(self.figure).__name__ + 'cursor_pos', self.center.copy())

        self.dyn_horizontal_line = self.figure.ax.axhline(self.pos[1],color='k', lw=1, ls='--',zorder=3)
        self.dyn_vertical_line = self.figure.ax.axvline(self.pos[0],color='k', lw=1, ls='--',zorder=3)

        self.sta_horizontal_line = self.figure.ax.axhline(self.pos[1],color=(1, 0, 0, 1), lw=1,zorder=2)
        self.sta_vertical_line = self.figure.ax.axvline(self.pos[0],color=(1, 0, 0, 1), lw=1,zorder=2)

        self.angle_line = self.figure.ax.axline((self.pos[0],self.pos[1]),lw=1,slope = 0)

        self.sta_horizontal_line.set_ydata(self.pos[1])#this is needed to be set once. This is so that .get_data() return the same form (for some reason)
        self.sta_vertical_line.set_xdata(self.pos[0])#this is needed to be set once. This is so that .get_data() return the same form (for some reason)

    def set_position(self):#called from botton
        position = []
        for entry in self.figure.overview.operations.cursor_position_entry:
            position.append(float(entry.get()))

        scaley = np.argmin(abs(self.figure.data[1]-position[1]))/len(self.figure.data[1])
        scalex = np.argmin(abs(self.figure.data[0]-position[0]))/len(self.figure.data[0])
        result = [scalex*(self.figure.xlimits[1]-self.figure.xlimits[0])+self.figure.xlimits[0],scaley*(self.figure.ylimits[0]-self.figure.ylimits[1])+self.figure.ylimits[1]]

        self.sta_horizontal_line.set_ydata(result[1])
        self.sta_vertical_line.set_xdata(result[0])
        self.draw_position(result)
        self.redraw()

    def reset_position(self):#caleld from botton
        self.dyn_horizontal_line.set_ydata(self.center[1])
        self.dyn_vertical_line.set_xdata(self.center[0])
        self.sta_horizontal_line.set_ydata(self.center[1])
        self.sta_vertical_line.set_xdata(self.center[0])
        self.angle_line._xy1 = self.center
        self.draw_position(self.center)
        self.redraw()

    def update_slope(self,angle):#called from slide in operations
        pos2 = [self.figure.xlimits[-1],math.tan(2*3.14159*float(angle)/360)*self.figure.ylimits[-1]]
        self.angle_line._slope = (self.center[1] - pos2[1])/(self.center[0] - pos2[0])
        self.figure.overview.operations.label2.configure(text=str(int(float(angle))))#update the number next to int range slide
        self.redraw()

    def update_event(self,event):
        offsets = [[65,425],[32,386]]

        event_x = max(event.x,offsets[0][0])
        event_x = min(event_x,offsets[0][1])
        test_x = offsets[0][1]*(self.figure.size[0]-offsets[0][0])/self.figure.size[0]
        scalex = (event_x-offsets[0][0])/test_x

        event_y = max(event.y,offsets[1][0])
        event_y = min(event_y,offsets[1][1])
        test_y = 0.9906*offsets[1][1]*(self.figure.size[1]-offsets[1][0])/self.figure.size[1]#need 0.9906 for some reason: but it is a scale so doesn't matter if it is slightly wrong
        scaley = (event_y-offsets[1][0])/test_y
        return [scalex*(self.figure.xlimits[1]-self.figure.xlimits[0])+self.figure.xlimits[0],scaley*(self.figure.ylimits[0]-self.figure.ylimits[1])+self.figure.ylimits[1]]

    def update_line_width(self):#254 seems to cover the whole plot. how to calculate exactly?
        self.sta_horizontal_line.set_linewidth(254*(self.figure.overview.figure_handeler.int_range*2+1)/len(self.figure.data[1]))
        self.sta_vertical_line.set_linewidth(254*(self.figure.overview.figure_handeler.int_range*2+1)/len(self.figure.data[0]))
        alpha = min(1,4/(self.figure.overview.figure_handeler.int_range*2+1))
        alpha = max(alpha,0.1)
        self.sta_horizontal_line.set_color((1, 0, 0, alpha))
        self.sta_vertical_line.set_color((1, 0, 0, alpha))
        self.redraw()

    def on_mouse_move(self, event):
        pos = self.update_event(event)
        self.dyn_horizontal_line.set_ydata(pos[1])
        self.dyn_vertical_line.set_xdata(pos[0])
        self.text.set_text('x=%1.2f, y=%1.2f' % (pos[0], pos[1]))
        self.draw_position(pos)
        self.redraw()

    def draw_position(self,pos):
        for index, label in enumerate(self.figure.overview.operations.cursor_labels):
            label.configure(text=str(round(float(pos[index]),2)))#update the number next

    def on_mouse_click(self,event):
        self.pos = self.update_event(event)
        self.sta_horizontal_line.set_ydata(self.pos[1])
        self.sta_vertical_line.set_xdata(self.pos[0])
        self.angle_line._xy1 = self.pos
        self.figure.click(self.pos)

    def redraw(self):
        self.figure.canvas.restore_region(self.figure.curr_background)
        self.figure.ax.draw_artist(self.text)
        self.figure.ax.draw_artist(self.dyn_horizontal_line)
        self.figure.ax.draw_artist(self.dyn_vertical_line)
        self.figure.ax.draw_artist(self.angle_line)
        self.figure.ax.draw_artist(self.sta_horizontal_line)
        self.figure.ax.draw_artist(self.sta_vertical_line)
        self.figure.canvas.blit(self.figure.ax.bbox)

class Horizontal_cursor():#not in use
    def __init__(self, figure):
        self.figure = figure

        self.text = self.figure.ax.text(0.5, 1, '', zorder=4,transform = self.figure.ax.transAxes,horizontalalignment='center',verticalalignment='top')
        self.figure.ax.add_artist(self.text)

        self.figure.xlimits = self.figure.xlimits
        self.figure.ylimits = self.figure.ylimits

        self.pos = self.figure.cursor.pos[1]

        thickness = 1
        self.up_line = self.figure.ax.axhline(self.pos+1,color='y', lw=thickness)
        self.down_line = self.figure.ax.axhline(self.pos-1,color='y', lw=thickness)

    def draw_sta_line(self):
        self.width=self.figure.overview.range
        thickness=self.figure.overview.int_range + 0.8

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
        return scaley*(self.figure.ylimits[0]-self.figure.ylimits[1])+self.figure.ylimits[1]#[scalex*(self.figure.xlimits[1]-self.figure.xlimits[0])+self.figure.xlimits[0],scaley*(self.figure.ylimits[0]-self.figure.ylimits[1])+self.figure.ylimits[1]]

    def drag(self,event):
        self.pos = self.update_event(event)
        self.up_line.set_ydata(self.pos+self.width)
        self.down_line.set_ydata(self.pos-+self.width)
        self.redraw()

    def get_position(self):
        return [self.pos-self.width,self.pos+self.width]

class Vertical_cursor():#not in use
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
