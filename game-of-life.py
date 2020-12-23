import tkinter as tk
import numpy as np
import copy
import time
from tkinter.filedialog import askopenfilename, asksaveasfilename
import re

# Change save file to pickle


class Cell:
    def __init__(self, col, row, alive=False):
        self.col = col
        self.row = row
        self.alive = alive

class Game:
    def __init__(self, n_cols, n_rows):
        self.n_cols = n_cols
        self.n_rows = n_rows
        self.alive_cells = {}
        self.updated_cells = {}
        self.cells = []
        for row in range(n_rows):
            col_list = []
            for col in range(n_cols):
                col_list.append(Cell(col, row))
            
            self.cells.append(col_list)

        self.cells = np.array(self.cells)

    def cell_clicked(self, row, col):
        self.update_cell( row, col)

    # Moves it in and out of lists and sets it to alive or dead
    def update_cell(self, row, col):
        if self.cells[row,col].alive:
            self.cells[row,col].alive = False
            del self.alive_cells[row,col] 
            self.updated_cells[(row, col)] = self.cells[row,col]

        elif not self.cells[row,col].alive:
            self.cells[row,col].alive = not self.cells[row,col].alive
            self.updated_cells[(row, col)] = self.cells[row,col]
            self.alive_cells[(row, col)] = self.cells[row,col]

    def update_board(self):
        cells_who_will_live = []
        cells_who_will_die = [] 
        checked_cells = [] 
        for key in self.alive_cells:
            cell_ = self.alive_cells[key]
            min_row = max(cell_.row-1, 0)
            min_col = max(cell_.col-1, 0)
            max_col = min(cell_.col+2, self.n_cols+1)
            max_row = min(cell_.row+2, self.n_rows+1)

            neighbours = self.cells[min_row:max_row, min_col:max_col].reshape(-1)
            for cell in neighbours:
                if cell in checked_cells:
                    continue
                
                checked_cells.append(cell)
                nr_alive_neighbours = self.get_nr_alive_neighbours(cell)

                if nr_alive_neighbours < 2 or nr_alive_neighbours > 3:
                    if cell.alive:
                        cells_who_will_die.append(cell)
                elif not cell.alive and nr_alive_neighbours==3:
                    cells_who_will_live.append(cell)
                else:
                    # It is alive and survives so no update
                    pass
                
        for cell in cells_who_will_die:
            self.update_cell(cell.row, cell.col)
        
        for cell in cells_who_will_live:
            self.update_cell(cell.row, cell.col)

    def get_nr_alive_neighbours(self, cell):
        nr_neighbours = 0
        for x in range(cell.col-1, cell.col+2):
            for y in range(cell.row-1, cell.row+2):
                try:
                    self.alive_cells[(y,x)]
                    nr_neighbours += 1
                except KeyError:
                    pass
        
        # since it counts it self as a neighbour decrease the nr of neighbours if it self is alive
        return nr_neighbours - 1*int(cell.alive)



    

class GUI:
    def __init__(self, n_rows, n_cols):
        self.max_width = 1080
        self.max_height = 720
        self.cell_height = 500
        self.cell_width = 500
        self.cell_margin = 0
        self.grid_border_width = 1# % of the cell_width
        self.bg_color = "#434547"
        self.grid_color = "white"
        self.fps = 60
        self.cell_height = 15
        self.cell_width = 15

        self.n_rows = n_rows
        self.n_cols = n_cols
        self.run_game = False
        self.step = False
        self.draw_board = False # Signals if the board should be drawn

        # Calculate the height and width of the cells
        height = n_rows*self.cell_height + 2*self.cell_margin
        width = n_rows*self.cell_width + 2*self.cell_margin
        self.grid_border_width *= self.cell_width/100

        # How many cells should be visable
        if height < self.max_height:
            self.n_rows_visable = self.n_rows
        else:
            self.n_rows_visable = int(self.max_height/self.cell_height)
            height = self.max_height
        
        if width < self.max_width:
            self.n_cols_visable = self.n_cols
        else:
            self.n_cols_visable = int(self.max_width/self.cell_width)
            width = self.max_width
        self.top_left_cell_x = max(0, (n_cols-self.n_cols_visable)/2)
        self.top_left_cell_y = max(0, (n_rows-self.n_rows_visable)/2)
            
        
        self.game = Game(n_cols, n_rows)
        self.top = tk.Tk()
        


        # Add canvas
        self.top.rowconfigure(0, minsize=25, weight=2)
        self.top.columnconfigure(1, minsize=25, weight=2)
        self.frame_canvas = tk.Frame(self.top)
        self.canvas = tk.Canvas(self.frame_canvas, bg=self.bg_color, height=height, width=width)
        self.frame_canvas.grid(row=0, column=1)
        self.canvas.bind("<Button-1>", self.cell_clicked)
        self.canvas.pack(fill=tk.BOTH)


        # Add buttons
        self.top.rowconfigure(0, minsize=height, weight=1)
        self.top.columnconfigure(0, minsize=75, weight=1)
        self.frame_buttons = tk.Frame(self.top)
        
        self.button_start_stop = tk.Button(self.frame_buttons, text="Start", command = lambda : self.start_button_clicked())
        self.frame_buttons.grid(row=0, column=0, sticky="n", padx=5, pady=5)
        self.button_start_stop.pack()
        
        self.button_step = tk.Button(self.frame_buttons, text="Step", command = lambda : self.button_step_clicked())
        self.button_step.pack()

        self.label_fps = tk.Label(self.frame_buttons, text="Fps")
        self.label_fps.pack()
        self.slider_fps = tk.Scale(self.frame_buttons, from_=1, to=120, command = lambda val : self.slider_fps_change(val))
        self.slider_fps.set(self.fps)
        self.slider_fps.pack()

        self.button_open = tk.Button(self.frame_buttons, text="Open", command=self.open_file)
        self.button_open.pack()
        self.button_save = tk.Button(self.frame_buttons, text="Save As...", command=self.save_file)
        self.button_save.pack()

        # Add sliders to move cells left and right and up and down
        self.frame_slider_row = tk.Frame(self.top)
        self.frame_slider_row.grid(row=0, column=3, padx=5)
        self.slider_row = tk.Scale(self.frame_slider_row, length = height, from_=0, to=n_rows-self.n_rows_visable, tickinterval=0, command = lambda val : self.row_slider_update(val))
        self.slider_row.set(self.top_left_cell_y)
        self.slider_row.pack()

        self.frame_slider_col = tk.Frame(self.top)
        self.frame_slider_col.grid(row=1, column=1, padx=5)
        self.slider_col = tk.Scale(self.frame_slider_col, length = width, from_=0, to=n_cols-self.n_cols_visable, tickinterval=0, command = lambda val : self.col_slider_update(val), orient=tk.HORIZONTAL)
        self.slider_col.set(self.top_left_cell_x)
        self.slider_col.pack()
        
        

        self.draw_grid()
        self.last_update = time.time()
        
    def row_slider_update(self, val):
        self.draw_board = True
        self.top_left_cell_y = int(val)
    
    def col_slider_update(self, val):
        self.draw_board = True
        self.top_left_cell_x = int(val)

    def open_file(self):
        """Open a file for editing."""
        filepath = askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        
        with open(filepath, "r") as input_file:
            game_data = input_file.read().split("\n")
            # The last element will be a \n. Remove this
            game_data.pop(-1)

            # Create the board
            for data in game_data:
                if "grid_size" in data:
                    size = [int(num) for num in re.findall(r'\d+', data)]
                    self.top.destroy()
                    self.__init__(size[0], size[1])
                    game_data.remove(data)
                    break
            
            # Fill the board
            for data in game_data:
                if "False" in data or not "True" in data:
                    continue
                index = [int(num) for num in re.findall(r'\d+', data)]
                self.game.update_cell(index[0], index[1])

            # Fix viewing location
            for data in game_data:
                if "top_left_coordinates:" in data:
                      top_left = [int(num) for num in re.findall(r'\d+', data)]
                      self.top_left_cell_y = top_left[0]
                      self.top_left_cell_x = top_left[1]
                      self.slider_row.set(self.top_left_cell_y)
                      self.slider_col.set(self.top_left_cell_x)
                      break
                
    def save_file(self):
        """Save the current file as a new file."""
        filepath = asksaveasfilename(
            defaultextension="txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not filepath:
            return
        with open(filepath, "w") as output_file:
            game_config = "grid_size:" + str(self.game.cells.shape) + "\n"
            board_txt = ""
            board_txt += "top_left_coordinates:" + str((self.top_left_cell_y,self.top_left_cell_x)) + "\n"
            for cell in self.game.cells.reshape(-1):
                board_txt +=  "row:" + str(cell.row) + "col:" + str(cell.col) + "alive:" + str(cell.alive)  +"\n"

            output_file.write(game_config)
            output_file.write(board_txt)

    def slider_fps_change(self, val):
        self.fps = float(val)

    def button_step_clicked(self):
        self.step = True
    
    def start_button_clicked(self):
        # switch text from start to stop
        # invert state of self.run_game
        self.run_game = not self.run_game
        if self.run_game:
              self.button_start_stop["text"] = "Stop"
        else:
            self.button_start_stop["text"] = "Start"
        
    def draw_square_in_cell(self, row, col, color):
        x0 = int(col*self.cell_width + self.cell_margin + self.grid_border_width /2)
        y0 = int(row*self.cell_height + self.cell_margin + self.grid_border_width /2)
        x1 = int((col+1)*self.cell_width + self.cell_margin - self.grid_border_width /2)
        y1 = int((row+1)*self.cell_height + self.cell_margin - self.grid_border_width /2)

        self.canvas.create_rectangle(x0, y0, x1, y1, fill = color)

    def clear_cell(self, location):
        row, col = location
        self.draw_square_in_cell(row, col, self.bg_color)

    def fill_cell(self, location):
        row, col = location
        self.draw_square_in_cell(row, col, "black")

    def cell_clicked(self, event):
        col = int((event.x-self.cell_margin)/self.cell_width)
        row = int((event.y-self.cell_margin)/self.cell_height)
        
        # Check for click outside of grid
        if col < 0 or col > self.n_cols_visable-1 or row < 0 or row > self.n_rows_visable-1: return

        # Calculate which cell was clicked
        col += self.top_left_cell_x
        row += self.top_left_cell_y

        self.game.cell_clicked(row, col)

    # Clear the board and redraw it. Only if something's been updated though
    def draw_updated(self):
        if len(self.game.updated_cells) == 0 and not self.draw_board: return

        gui.canvas.delete("all")

        x_visible = range(self.top_left_cell_x, self.top_left_cell_x + self.n_cols_visable)
        y_visible = range(self.top_left_cell_y, self.top_left_cell_y + self.n_rows_visable)
        for key in self.game.alive_cells:
            # Check if the cell is visible
            if key[0] in y_visible and key[1] in x_visible:
                location = (key[0] - self.top_left_cell_y, key[1] - self.top_left_cell_x)
                self.fill_cell(location)

        self.game.updated_cells = {}
        self.draw_board = False

        self.draw_grid()
        
    def update(self):
        if self.step:
            self.game.update_board()
            self.step = False
        elif self.run_game:
            if (time.time() - self.last_update) > 1/self.fps:
                self.game.update_board()
                self.last_update = time.time()
        self.draw_updated()

    def draw_grid(self):
        # Draw rows
        for y in range(self.n_rows + 1):
            x0 = int(0 + self.cell_margin)
            y0 = int(y*self.cell_height + self.cell_margin)
            x1 = int(self.n_cols*self.cell_width + self.cell_margin)
            y1 = int(y*self.cell_height + self.cell_margin)
            self.canvas.create_line(x0, y0, x1, y1, fill=self.grid_color, width = self.grid_border_width)  

        # Draw cols
        for x in range(self.n_cols + 1):
            x0 = int(x*self.cell_width + self.cell_margin)
            y0 = int(0 + self.cell_margin)
            x1 = int(x*self.cell_width + self.cell_margin)
            y1 = int(self.n_rows*self.cell_height + self.cell_margin)
            self.canvas.create_line(x0, y0, x1, y1, fill=self.grid_color, width = self.grid_border_width) 




gui = GUI(300,300)

while True:
    gui.update()
    gui.top.update_idletasks()
    gui.top.update()









