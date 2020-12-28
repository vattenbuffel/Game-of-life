import tkinter as tk
import numpy as np
import copy
import time
from tkinter.filedialog import askopenfilename, asksaveasfilename
import re
from queue import Queue
import pickle
import threading

# TODO:Add functionality to rotate structures


class Cell:
    def __init__(self, col, row, alive=False):
        self.col = col
        self.row = row
        self.alive = alive
        self.drawing = None
    
    def copy(self):
        cell = Cell(self.col, self.row, alive=self.alive)
        cell.drawing = self.drawing
        return cell

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
            self.kill_cell(row, col)

        elif not self.cells[row,col].alive:
            self.revive_cell(row, col)

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

    def revive_cell(self, row, col):
        self.cells[row,col].alive = True
        self.updated_cells[(row, col)] = self.cells[row,col]
        self.alive_cells[(row, col)] = self.cells[row,col]

    def kill_cell(self, row, col):
        self.cells[row,col].alive = False
        self.updated_cells[(row, col)] = self.cells[row,col]
        del self.alive_cells[row,col] 

    def kill_cells_all(self):
        for cell in self.alive_cells.values():
            cell.alive = False
            self.updated_cells[(cell.row, cell.col)] = cell
        self.alive_cells = {}


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

# Saves the locations of the alive cells with respect to the mouse pointer
class Structure:
    def __init__(self, alive_cells):
        self.alive_cells = alive_cells

# This should be the function given to a thread in order to save structures
# args sent to the thread is a tuple of a queue on which the upper left and bottom right cells will be put and
# the board it self and locks for getting the save and open file paths and a lock to signal when done
# and a queue on which to add blinking cells, 
# args = (queue, board, lock_save, lock_done)
def save_structure(data_queue, board, lock_save, lock_done, queue_blink):
    # Get the upper left and bottom right corner
    popupmsg("Chose top left corner")
    upper_left_row, upper_left_col  = data_queue.get()
    queue_blink.put((board[upper_left_row, upper_left_col], True))

    popupmsg("Chose bottom right corner")
    bottom_right_row, bottom_right_col = data_queue.get()


    # If bottom right is above top left
    if upper_left_row > bottom_right_row or upper_left_col > bottom_right_col:
        popupmsg("Invalid cells chosen")
        queue_blink.put((board[upper_left_row, upper_left_col], False))
        lock_done.release()
        return
    
    alive_cells = []
    for cell in board[upper_left_row:bottom_right_row+1, upper_left_col:bottom_right_col+1].reshape(-1):
        if cell.alive:
            cell_cpy = cell.copy() 
            alive_cells.append(cell_cpy)

    # If all the chosen cells were dead inform the user and abort the save
    if len(alive_cells) == 0:
        popupmsg("You chose no living cells")
        queue_blink.put((board[upper_left_row, upper_left_col], False))
        lock_done.release()
        return

    
    
    top_row = 10**100
    leftest_col = 10**100
    for cell in alive_cells:
        if cell.row < top_row: top_row = cell.row

        if cell.col < leftest_col: leftest_col = cell.col
    
    # Move all the cells left and up
    for cell in alive_cells:
        cell.row -= top_row
        cell.col -= leftest_col


    
    # Get the save filepath
    lock_save.release()
    file_path = data_queue.get()
    if file_path: # Check if correct file path
        save_dict = {"is_structure_save":True, "alive_cells":alive_cells}
        pickle.dump(save_dict, open(file_path, "wb" ))

    queue_blink.put((board[upper_left_row, upper_left_col], False))
    lock_done.release()
    
def popupmsg(msg):
    def fun_to_run(msg):
        popup = tk.Tk()
        popup.wm_title("!")
        label = tk.Label(popup, text=msg, font=("Helvetica", 10))
        label.pack(side="top", fill="x", pady=10)
        B1 = tk.Button(popup, text="Okay", command = popup.destroy)
        B1.pack()
        popup.bind("<KeyPress>", lambda event: popup.destroy())
        popup.mainloop()

    thread = threading.Thread(target = lambda: fun_to_run(msg))
    thread.start()
    thread.join()

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

        self.button_clear = tk.Button(self.frame_buttons, text="Clear", command = self.button_clear_clicked)
        self.button_clear.pack()

        self.label_fps = tk.Label(self.frame_buttons, text="Fps")
        self.label_fps.pack()
        self.slider_fps = tk.Scale(self.frame_buttons, from_=1, to=120, command = lambda val : self.slider_fps_change(val))
        self.slider_fps.set(self.fps)
        self.slider_fps.pack()

        self.button_open = tk.Button(self.frame_buttons, text="Open Board", command=self.open_board)
        self.button_open.pack()
        self.button_save = tk.Button(self.frame_buttons, text="Save Board As...", command=self.save_board)
        self.button_save.pack()

        self.button_save_structure = tk.Button(self.frame_buttons, text="Open Structure", command=self.open_structure)
        self.button_save_structure.pack()
        self.button_open_structure = tk.Button(self.frame_buttons, text="Save Structure As...", command=self.save_structure)
        self.button_open_structure.pack()

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


        # This is for passing data from and to threads who save and load structures
        # One should probably not use threads for this but I want to learn
        self.queue_structure = None
        self.lock_structure_get_save_filepath = threading.Lock()
        self.lock_structure_get_save_filepath.acquire(0)
        self.lock_save_structure_done = threading.Lock()
        self.lock_save_structure_done.acquire(0)
        self.structure_to_place = []

        # Handle blinking cells
        self.blinking_cells = set()
        self.blinking_hz = 2
        self.last_blink = time.time()
        self.blinking_state = False
        self.queue_blinking_receive = Queue() # To pass cells which should be added or removed from blinking cells. Send tuples (cell, True/False)

        # Get mouse location
        self.top.bind('<Motion>', self.update_mouse_position)
        self.mouse_col, self.mouse_row = None, None

        # Handle keyboard presses
        self.top.bind("<KeyPress>", self.keyboard_pressed)

    def button_clear_clicked(self):
        self.game.kill_cells_all()

    def keyboard_pressed(self, event):
        if event.char == 'j':
            self.slider_row.set(self.top_left_cell_y + 1)
        elif event.char == 'k':
            self.slider_row.set(self.top_left_cell_y - 1)
        elif event.char == 'h':
            self.slider_col.set(self.top_left_cell_x - 1)
        elif event.char == 'l':
            self.slider_col.set(self.top_left_cell_x + 1)

    # Also clear the structure to draw
    def update_mouse_position(self, event):
        col = int((event.x-self.cell_margin)/self.cell_width)
        row = int((event.y-self.cell_margin)/self.cell_height)
        self.mouse_col, self.mouse_row = col, row

        for cell in self.structure_to_place:
            self.canvas.delete(cell.drawing)
            self.refill_cell(cell, -self.mouse_row, -self.mouse_col)

    def open_structure(self):
        filepath = self.get_open_path()
        if not filepath:
            return
        save_dict = pickle.load( open( filepath, "rb" ))

        # Check if it's a saved structure
        try:
            save_dict["is_structure_save"]
        except:
            popupmsg("Invalid save file chosen")
            return

        self.structure_to_place = save_dict["alive_cells"]

    def save_structure(self):
        self.queue_structure = Queue()
        args = (self.queue_structure, self.game.cells, self.lock_structure_get_save_filepath, self.lock_save_structure_done, self.queue_blinking_receive)
        thread = threading.Thread(target = save_structure, args=args)
        thread.start()

    def row_slider_update(self, val):
        self.draw_board = True
        self.top_left_cell_y = int(val)
    
    def col_slider_update(self, val):
        self.draw_board = True
        self.top_left_cell_x = int(val)

    # Opens the board and sets the viewing location
    def open_board(self):
        filepath = self.get_open_path()
        
        if not filepath:
            return
        
        save_dict = pickle.load( open( filepath, "rb" ))

        # Check if opend a board save
        try:
            save_dict["is_board_save"]
        except:
            popupmsg("Invalid save file chosen")
            return

        board_shape = save_dict["grid_size"]
        top_left_coordinates = save_dict["top_left_coordinates"]
        alive_Cells = save_dict["alive_cells"]

        self.top.destroy()
        self.__init__(board_shape[0], board_shape[1])        
        self.slider_row.set(top_left_coordinates[0])
        self.slider_col.set(top_left_coordinates[1])
        self.game.alive_cells = alive_Cells
        
    def get_open_path(self):
        filepath = askopenfilename(
            filetypes=[("Pickle files", "*.p"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        return filepath

    # Saves the board and viewing location
    def save_board(self):
        filepath = self.get_save_path()
        if not filepath: return

        dict_to_save = {"is_board_save":True, "grid_size":None, "top_left_coordinates":None, "alive_cells":None}

        dict_to_save["grid_size"] = self.game.cells.shape
        dict_to_save["top_left_coordinates"] = (self.top_left_cell_y,self.top_left_cell_x)
        dict_to_save["alive_cells"] = self.game.alive_cells
        
        pickle.dump(dict_to_save, open(filepath, "wb" ))
        
    def get_save_path(self):
        filepath = asksaveasfilename(
            defaultextension="txt",
            filetypes=[("Pickle files", "*.p"), ("Text Files", "*.txt"), ("All Files", "*.*"), ],
        )
        return filepath

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
        x0 = int(col*self.cell_width + self.cell_margin + max(1, self.grid_border_width))
        y0 = int(row*self.cell_height + self.cell_margin + max(1, self.grid_border_width))
        x1 = int((col+1)*self.cell_width + self.cell_margin - self.grid_border_width /2)
        y1 = int((row+1)*self.cell_height + self.cell_margin - self.grid_border_width /2)

        return self.canvas.create_rectangle(x0, y0, x1, y1, fill = color)

    def refill_cell(self, cell, offset_row, offset_col):
        self.canvas.delete(cell.drawing)
        cell.drawing = self.fill_cell((cell.row-offset_row, cell.col-offset_col))

    def fill_cell(self, location):
        row, col = location
        return self.draw_square_in_cell(row, col, "black")

    def cell_clicked(self, event):
        col = int((event.x-self.cell_margin)/self.cell_width)
        row = int((event.y-self.cell_margin)/self.cell_height)
        
        # Check for click outside of grid
        if col < 0 or col > self.n_cols_visable-1 or row < 0 or row > self.n_rows_visable-1: return

        # Calculate which cell was clicked
        col += self.top_left_cell_x
        row += self.top_left_cell_y

        # If the strcture queue is not None then the cell should go to the queue
        if self.queue_structure is not None:
            self.queue_structure.put((row, col))
            return
        
        # If there's a structure to place it should be placed
        if len(self.structure_to_place) > 0:
            for cell in self.structure_to_place:
                self.game.revive_cell(cell.row+self.mouse_row+self.top_left_cell_y, cell.col+self.mouse_col+self.top_left_cell_x)
                self.canvas.delete(cell.drawing)
            self.structure_to_place = []
            return

        # Game should register that a cell was clicked on
        self.game.cell_clicked(row, col)

    # Clear the board and redraw it. Only if something's been updated though
    def draw_updated(self):
        if len(self.game.updated_cells) == 0 and not self.draw_board: return

        # Clar the board of alive cells and those who were alive but are dead now
        for key in self.game.updated_cells:
            gui.canvas.delete(self.game.updated_cells[key].drawing)
        for key in self.game.alive_cells:
            gui.canvas.delete(self.game.alive_cells[key].drawing)


        # Add the updated cells to the filled cells list and draw them
        x_visible = range(self.top_left_cell_x, self.top_left_cell_x + self.n_cols_visable)
        y_visible = range(self.top_left_cell_y, self.top_left_cell_y + self.n_rows_visable)
        for key in self.game.alive_cells:
            # Check if the cell is visible
            if key[0] in y_visible and key[1] in x_visible:
                location = (key[0] - self.top_left_cell_y, key[1] - self.top_left_cell_x)
                self.game.alive_cells[key].drawing = self.fill_cell(location)
                

        self.game.updated_cells = {}
        self.draw_board = False

    # Draw all cells which should blink, including structure to place
    def draw_blinking(self):
        # Is it time to blink
        if time.time() - self.last_blink > 1/self.blinking_hz:
            for cell in self.blinking_cells:
                if not self.blinking_state:  
                    self.canvas.delete(cell.drawing)
                else:
                    self.refill_cell(cell, self.top_left_cell_y, self.top_left_cell_x)
                    
            # Draw structure to place
            for cell in self.structure_to_place:
                if not self.blinking_state:  
                    self.canvas.delete(cell.drawing)
                else:
                    self.refill_cell(cell, -self.mouse_row, -self.mouse_col)

            self.blinking_state = not self.blinking_state
            self.last_blink = time.time()

    def update(self):
        # Progress the game
        if self.step:
            self.game.update_board()
            self.step = False
        elif self.run_game:
            if (time.time() - self.last_update) > 1/self.fps:
                self.game.update_board()
                self.last_update = time.time()
        self.draw_updated()

        # If it should get the filepath for the save structure
        if self.lock_structure_get_save_filepath.acquire(0):
            self.queue_structure.put(self.get_save_path())
        
        # Is the save thread done
        if self.lock_save_structure_done.acquire(0):
            self.queue_structure = None


        # Handle blinking cells
        # Get/remove blinking cells from other threads
        try:
            cell, add = self.queue_blinking_receive.get_nowait()
            if add:
                self.blinking_cells.update([cell])
            else:
                self.blinking_cells.remove(cell)
                # Redraw it to the proper fill or clear
                if cell.alive:
                    self.refill_cell(cell,self.top_left_cell_y, self.top_left_cell_x)
                else:
                    self.canvas.delete(cell.drawing)
                    
        except:
            pass
        self.draw_blinking()
        
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









