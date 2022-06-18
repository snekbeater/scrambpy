#!/usr/bin/python3
#########################################################################################################
#
# Scramb.py Studio is a GUI for Scramb.py, a region based JPEG Image Scrambler
#
VERSION = "0.0.1 alpha"
#
# For updates see git repo at:
# https://github.com/snekbeater/scrambpy
#
# Author:  Snekbeater
# Contact: snekbeater at protonmail.com
#
# Copyright (C) 2022 snekbeater
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#########################################################################################################



from PIL import  ImageDraw, ImageFilter, ImageChops # TODO automated install
from PIL import Image as PilImage # to not mess with Tk.Image
from PIL import ImageTk

import os
import subprocess
import math
from sys import platform # to find out which OS we are running on

from tkinter import * # TODO automated install
from tkinter.messagebox import showinfo


from tkinter import filedialog as filedialog
from tkinter import ttk

import tkinter.font as font

import tkinter as tk

#########################################################################################################
# attr
#########################################################################################################

currentImage = None
canvas = None
image_container = None
xscrollbar = None
yscrollbar = None
containerimage = None
img = None
frame = None
brush = None
overlayGrid = None
window = None
filename = ""
currentOS = ""

paintWindow = None


filemenu = None
helpmenu = None
toolbarButtons = {}



#########################################################################################################
# Classes
#########################################################################################################



class OverlayGrid:
	def __init__(self, canvas, image):
		self.canvas = canvas
	
#		print(self.canvas.cget("width"))
		#self.width = int(self.canvas.winfo_width() / 8)
		#self.height = int(self.canvas.winfo_height() / 8)

		self.width = int(image.width() / 8)
		self.height = int(image.height() / 8)

	
		self.grid = []
	
		for x in range(0,self.width):
			self.grid.append([])
			for y in range(0,self.height):
				self.grid[x].append(self.canvas.create_rectangle(x * 8, y * 8, x * 8 + 8, y * 8 + 8))


	def markBlocks(self, center, radius, circle=False, unmark=False):
	
		#print("center given at",center)
		firstx = center[0] - radius
		if firstx < 0:
			firstx = 0
	
		lastx = center[0] + radius
		if lastx > self.width*8:
			lastx = self.width*8


		firsty = center[1] - radius
		if firsty < 0:
			firsty = 0
	
		lasty = center[1] + radius
		if lasty > self.height*8:
			lasty = self.height*8


		#print("pix:",firstx, lastx, firsty, lasty)




		blockfirstx = int(firstx / 8)
		blocklastx = int(math.ceil(lastx / 8))
		
		blockfirsty = int(firsty / 8)
		blocklasty = int(math.ceil(lasty / 8))

		#print(blockfirstx, blocklastx, blockfirsty, blocklasty)



		for x in range(blockfirstx,blocklastx):
			for y in range(blockfirsty,blocklasty):
				#print("mark",x,y)
					
					
				x0, y0, x1, y1 = self.canvas.coords(self.grid[x][y])
				distance = math.hypot(x0 + 4 - center[0], y0 + 4 - center[1])
					
				if not circle or distance < radius:
					if unmark:
						self.canvas.itemconfig(self.grid[x][y], fill='')
					else:
						self.canvas.itemconfig(self.grid[x][y], fill='red')
			

	def createImageFromGrid(self):
		maskDimensions = (self.width * 8, self.height * 8)
		mode = '1'
		color = (0)
		pngim = PilImage.new(mode, maskDimensions, color)	

		for x in range(0, len(self.grid)):
			for y in range(0, len(self.grid[x])):
				if self.canvas.itemcget(self.grid[x][y], "fill") == 'red':
					pngimDraw = ImageDraw.Draw(pngim)
					pngimDraw.rectangle((x*8, y*8,x*8+8,y*8+8), fill=(1))

		return pngim


	def loadGridFromImageFile(self, filename):
		pngim = PilImage.open(filename)

		if not pngim.size == (self.width, self.height):
			pngim = pngim.resize((self.width, self.height), resample=PilImage.NEAREST)
		pngim = pngim.convert("1", dither=False)

		for x in range(0, len(self.grid)):
			for y in range(0, len(self.grid[x])):
				luma = pngim.getpixel((x,y))			
				if luma == 0:
					self.canvas.itemconfig(self.grid[x][y], fill='')
				else:
					self.canvas.itemconfig(self.grid[x][y], fill='red')


	def destroyOverlayGrid(self):
		for x in range(0, len(self.grid)):
			for y in range(0, len(self.grid[x])):
				self.canvas.delete(self.grid[x][y])




class PaintWindow:
	currentImageFilename = None
	currentImagePil = None
	canvas = None
	canvasImageContainer = None
	xscrollbar = None
	yscrollbar = None
	currentImageTk = None
	frame = None
	brush = None
	circleBrush = None
	rectangleBrush = None
	brushradius = 32
	overlayGrid = None
	circleBrushSelected = True
	eraserSelected = False

	def __init__(self,imageframe):
		self.frame = Frame(imageframe, bd=2, relief=SUNKEN)

		self.frame.grid_rowconfigure(0, weight=1)
		self.frame.grid_columnconfigure(0, weight=1)

		self.xscrollbar = Scrollbar(self.frame, orient=HORIZONTAL)
		self.xscrollbar.grid(row=1, column=0, sticky=E+W)

		self.yscrollbar = Scrollbar(self.frame)
		self.yscrollbar.grid(row=0, column=1, sticky=N+S)

		self.canvas = Canvas(self.frame, bd=0, xscrollcommand=self.xscrollbar.set, yscrollcommand=self.yscrollbar.set)
		self.canvas.grid(row=0, column=0, sticky=N+S+E+W)


		self.canvas.bind("<Motion>", self.toolMoved)



		self.frame.pack(fill = BOTH, expand=1)


	def toolClicked(self, event):
		if self.overlayGrid != None:
			#print("Tool clicked")

			pixx, pixy = (int(self.canvas.canvasx(event.x)),int(self.canvas.canvasy(event.y)))

			#print("real pixel pos", pixx, pixy)


			# TODO first click is thus always paint, even when right mouse is clicked (erase)
			self.overlayGrid.markBlocks((pixx,pixy), self.brushradius, circle=self.circleBrushSelected, unmark=self.eraserSelected)

			self.canvas.update()
			self.frame.update()


	def toolRightClicked(self, event):
		if self.overlayGrid != None:
			#print("Tool clicked")

			pixx, pixy = (int(self.canvas.canvasx(event.x)),int(self.canvas.canvasy(event.y)))

			#print("real pixel pos", pixx, pixy)


			# TODO first click is thus always paint, even when right mouse is clicked (erase)
			self.overlayGrid.markBlocks((pixx,pixy), self.brushradius, circle=self.circleBrushSelected, unmark=not self.eraserSelected)

			self.canvas.update()
			self.frame.update()




	def toolMoved(self,event):

		#print(event)
		#print("Scrollbar X:",self.xscrollbar.get())

		if self.brush != None:
		
			'''
			if self.currentImagePil.width - int(self.canvas.winfo_width()) > 0:
				xOffset = int((self.xscrollbar.get()[0] / (1 - (self.xscrollbar.get()[1] - self.xscrollbar.get()[0]))) * (self.currentImagePil.width - int(self.canvas.winfo_width())))
			else:
				xOffset = 0
			
			print("canvasx()",self.canvas.canvasx(event.x))
			
	
			if self.currentImagePil.height - int(self.canvas.winfo_height()) > 0:
				yOffset = int((self.yscrollbar.get()[0] / (1 - (self.yscrollbar.get()[1] - self.yscrollbar.get()[0]))) * (self.currentImagePil.height - int(self.canvas.winfo_height())))
			else:
				yOffset = 0
				
				
			
			self.canvas.moveto(self.brush,event.x + xOffset, event.y + yOffset)
			'''

			# get real pixel position of event on canvas
			pixx, pixy = (int(self.canvas.canvasx(event.x)),int(self.canvas.canvasy(event.y)))

			#print("real pixel pos", pixx, pixy)

			self.canvas.moveto(self.rectangleBrush, pixx-self.brushradius, pixy-self.brushradius)
			self.canvas.moveto(self.circleBrush, pixx-self.brushradius, pixy-self.brushradius)



#			self.canvas.update()

			
			if event.state&256==256 and self.overlayGrid != None:
				#print("Tool clicked")
				self.overlayGrid.markBlocks((pixx, pixy), self.brushradius, circle=self.circleBrushSelected, unmark=self.eraserSelected)

			if event.state&1024==1024 and self.overlayGrid != None:
				#print("Tool clicked")
				self.overlayGrid.markBlocks((pixx, pixy), self.brushradius, circle=self.circleBrushSelected, unmark=not self.eraserSelected)


			self.canvas.update()
	



	def loadImage(self, filename):
	
		self.currentImageFilename = filename
		self.currentImagePil = PilImage.open(filename)

		print("Image size ", self.currentImagePil.size)


		if not self.currentImagePil.mode == "RGB":
			print("Image mode is",self.currentImagePil.mode,", converting it to RGB")
			self.currentImage = self.currentImagePil.convert("RGB")


		# TODO check if a _mask.png exists and ask if you want to load it <= no, must be done in main open def
	
	
		# fill none-8 images as Scrambpy would do it
		originalWidth, originalHeight = self.currentImagePil.size
		if (originalWidth % 8 > 0) or (originalHeight % 8 > 0):
			# correct % 8 > 0 images
			originalIm = self.currentImagePil.copy()
			newWidth = int(math.ceil(originalWidth / 8)*8)
			newHeight = int(math.ceil(originalHeight / 8)*8)

			self.currentImagePil = self.currentImagePil.crop((0,0, newWidth, newHeight ))


			overscanColumns = 8 - originalWidth % 8
			if overscanColumns < 8:
				print("Filling right side overscan")
				rightStrip = originalIm.copy().crop((originalIm.width - 1,0,originalIm.width ,originalIm.height))
				for i in range(overscanColumns):
					self.currentImagePil.paste(rightStrip,(originalIm.width + i, 0),mask=None)
			overscanLines = 8 - originalIm.height % 8
			if overscanLines < 8:
				print("Filling bottom overscan")
				bottomStrip = originalIm.copy().crop((0, originalIm.height - 1,originalIm.width,originalIm.height))
				for i in range(overscanLines):
					self.currentImagePil.paste(bottomStrip,(0,originalIm.height + i),mask=None)


	
		
		#Pil Image => Tkinter image
		self.currentImageTk = ImageTk.PhotoImage(self.currentImagePil)

	
	
	
	
		self.canvasImageContainer = self.canvas.create_image(0,0,image=self.currentImageTk, anchor="nw")

		#self.canvas.itemconfig(image_container,image=img)    # TODO =???? after rework, needed??? wrong vari name used...

		self.canvas.configure(scrollregion=self.canvas.bbox("all")) # set the new dimensions for the scrollbars
	
		self.xscrollbar.config(command=self.canvas.xview)
		self.yscrollbar.config(command=self.canvas.yview)



		# setup overlay
	
	
		if self.overlayGrid != None:
			self.overlayGrid.destroyOverlayGrid()
		self.overlayGrid = OverlayGrid(self.canvas,self.currentImageTk)
	
		self.canvas.bind("<Button-1>", self.toolClicked)
		self.canvas.bind("<Button-3>", self.toolRightClicked)

		# setup brush

		
		self.rectangleBrush = self.canvas.create_rectangle(0, 0, self.brushradius*2, self.brushradius*2, outline='red', width=2, state="hidden")
		self.circleBrush = self.canvas.create_oval(0, 0, self.brushradius*2, self.brushradius*2, outline='red', width=2, state="hidden")
		self.brush = self.circleBrush
		
	
	
		#		canvas.move(a, 20, 20)

	#	canvas.itemconfigure(id, state='hidden'/'normal')



		self.canvas.update()
		self.frame.update()

		self.setBrushSize(self.brushradius)
		if self.circleBrushSelected:
			self.setBrushCircle()
		else:
			self.setBrushRectangle()
	



	def setBrushSize(self, radius):


		self.brushradius = radius

		if self.brush != None:

			x0, y0, x1, y1 = self.canvas.coords(self.brush)
			posx = int(x1 - ((x1 - x0) / 2))
			posy = int(y1 - ((y1 - y0) / 2))
		
		
			self.canvas.coords(self.circleBrush, posx - radius, posy - radius, posx + radius, posy + radius)
			self.canvas.coords(self.rectangleBrush, posx - radius, posy - radius, posx + radius, posy + radius)


			self.canvas.update()


	def setBrushRectangle(self):

		self.canvas.itemconfigure(self.rectangleBrush, state='normal')
		self.canvas.itemconfigure(self.circleBrush, state='hidden')

		self.brush = self.rectangleBrush
		self.circleBrushSelected = False
		
		self.canvas.update()

	def setBrushCircle(self):

		self.canvas.itemconfigure(self.rectangleBrush, state='hidden')
		self.canvas.itemconfigure(self.circleBrush, state='normal')

		self.brush = self.circleBrush
		self.circleBrushSelected = True
		
		self.canvas.update()

	def setBrushSelected(self):
		self.eraserSelected = False

	def setEraserSelected(self):
		self.eraserSelected = True



#########################################################################################################
# defs
#########################################################################################################




def donothing():
	x = 0
   

def openImage():

	global paintWindow
	global filename
		
	filetypes = (
		('jpeg images', '*.jpg'),
		('all files', '*.*')
	)

	filename = filedialog.askopenfilename(
		title='Open image',
		#initialdir='/',
		filetypes=filetypes)

#	showinfo(
#		title='Selected File',
#		message=filename
#	)
	
	if len(filename) > 0:	
		paintWindow.loadImage(filename)

		#image_container.update()

		activateImageMenuEntries()


		updateTitleBar()

	
		print("done loading")



def brushSizeSliderChanged(event):
	global paintWindow

	#print(event)
	
	paintWindow.setBrushSize(int(int(event)/2))



def activateImageMenuEntries():
	global filemenu
	global helpmenu

	filemenu.entryconfigure("Open mask image ...", state=tk.NORMAL)
	filemenu.entryconfigure("Save mask image as ...", state=tk.NORMAL)




def saveMaskImageAs():

	filetypes = (
		('png images', '*.png'),
		('all files', '*.*')
	)

	filename = filedialog.asksaveasfilename(
		title='Save mask image',
		#initialdir='/',
		filetypes=filetypes)

	if len(filename) > 0:
		saveMaskImage(filename)
		
		showinfo(
			title='Save mask...',
			message="Mask saved!"
			)
	
		
def saveMaskImage(filename):
	global paintWindow
	
	pngim = paintWindow.overlayGrid.createImageFromGrid()
	
	pngim.save(filename)



def openMaskImage():

	global paintWindow

	filetypes = (
		('png images', '*.png'),
		('all files', '*.*')
	)

	filename = filedialog.askopenfilename(
		title='Open mask image',
		#initialdir='/',
		filetypes=filetypes)

#	showinfo(
#		title='Selected File',
#		message=filename
#	)
	

	paintWindow.overlayGrid.loadGridFromImageFile(filename)



def toolChangeRectangle():
	global paintWindow
	global toolbarButtons
	
	paintWindow.setBrushRectangle()
	toolbarButtons['rectangle'].config(relief="sunken")
	toolbarButtons['circle'].config(relief="raised")
	

def toolChangeCircle():
	global paintWindow

	paintWindow.setBrushCircle()

	toolbarButtons['rectangle'].config(relief="raised")
	toolbarButtons['circle'].config(relief="sunken")




def toolChangeBrush():
	global paintWindow
	global toolbarButtons
	
	paintWindow.setBrushSelected()
	toolbarButtons['brush'].config(relief="sunken")
	toolbarButtons['eraser'].config(relief="raised")



def toolChangeEraser():
	global paintWindow
	global toolbarButtons
	
	paintWindow.setEraserSelected()
	toolbarButtons['eraser'].config(relief="sunken")
	toolbarButtons['brush'].config(relief="raised")



def exportScrambledImage():
	
	global paintWindow
	global filename


	# TODO Export window
	
	maskfilename = os.path.splitext(filename)[0]+'_scst_mask.png'
	outputfilename = os.path.splitext(filename)[0]+'_scst_scrambled.jpg'


	showinfo(
		title='Export...',
			message="Export is very experimental!\n\r\n\rAt this time no error is displayed, you just do not get any result.\n\r\n\rMask and scrambled image are saved with the name including _scst_. Make sure these do not exist.\n\r\n\rscramb.py needs to be placed next to scrambpystudio.py, and will be called now..."
			)
	


	saveMaskImage(maskfilename)
	
	
	# TODO python3 path??, just "python" results in python2 to be used on some systems... (syntax error on scrambpys "->")
	# this call is so much an MVP... :-)
	if isRunOnLinux() or isRunOnMac():
		subprocess.Popen(["python3", "scramb.py", "-i",paintWindow.currentImageFilename,"-m",maskfilename,"-o",outputfilename,"-s","ultra","-2"])
	else:
		subprocess.Popen(["python", "scramb.py", "-i",paintWindow.currentImageFilename,"-m",maskfilename,"-o",outputfilename,"-s","ultra","-2"])
	

	showinfo(
		title='Export...',
			message="Done"
			)
	


def updateTitleBar():

	global window
	global filename
	global VERSION

	title = "Scramb.py Studio " + VERSION

	if filename != "":
		fn = os.path.basename(filename)
		title = fn + " - " + title

	window.title(title)


def showAboutWindow():

	global VERSION
	
	text = "Scramb.py Studio\n\r"
	text = text + "\n\r"
	text = text + "GUI for Scramb.py, a region based JPEG Image Scrambler\n\r"
	text = text + "\n\r"
	text = text + "Version  "+VERSION+"  Copyright \u00A9 2022 by snekbeater\n\r"
	text = text + "For updates see git repo at https://github.com/snekbeater/scrambpy\n\r"
	text = text + "This program comes with ABSOLUTELY NO WARRANTY.\n\r"
	text = text + "This is free software, and you are welcome to redistribute it under certain conditions; see code for details."
	

	showinfo("About Scramb.py Studio",text)


def isRunOnLinux():
	return platform == "linux" or platform == "linux2"


def isRunOnWindows():
	return platform == "win32"


def isRunOnMac():
	return platform == "darwin"



#########################################################################################################
# Build main Window
#########################################################################################################

window = Tk()


if isRunOnWindows():
	window.state('zoomed') # works only on windows

if isRunOnLinux() or isRunOnMac():
	window.attributes('-zoomed', True) # works only on Linux



updateTitleBar()


#########################################################################################################
# Menu bar
#########################################################################################################

menubar = Menu(window)
filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Open image ...", command=openImage)
filemenu.add_separator()
filemenu.add_command(label="Open mask image ...", command=openMaskImage, state=tk.DISABLED)
filemenu.add_command(label="Save mask image as ...", command=saveMaskImageAs, state=tk.DISABLED)


filemenu.add_separator()
filemenu.add_command(label="Exit", command=window.quit)
menubar.add_cascade(label="File", menu=filemenu)



scramblermenu = Menu(menubar, tearoff=0)
scramblermenu.add_command(label="Export scrambled image ...", command=exportScrambledImage)
menubar.add_cascade(label="Scramble", menu=scramblermenu)






helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_command(label="About...", command=showAboutWindow)
menubar.add_cascade(label="Help", menu=helpmenu)

window.config(menu=menubar)



#########################################################################################################
# Frames
#########################################################################################################


# TODO nice frame at the bottom with an export button and scrambler parameters => maybe later, first mvp ;-)
#controlframe = Frame(window, height = 100)
#controlframe.pack( side = BOTTOM, fill = X )
#b = Button(controlframe,text="Scramble!", command=donothing,state=tk.DISABLED)
#b.pack(side=RIGHT, fill = Y)


toolbarframe = Frame(window, width = 70)

f = font.Font(size=10)
b = Button(toolbarframe,text="brush", font=f, command=toolChangeBrush, relief="sunken")
b.pack(fill = X)
toolbarButtons["brush"] = b

b = Button(toolbarframe,text="eraser", font=f, command=toolChangeEraser)
b.pack(fill = X)
toolbarButtons["eraser"] = b


s = ttk.Separator(toolbarframe, orient='horizontal')
s.pack(fill='x', pady=3)



b = Button(toolbarframe,text="rect.", font=f, command=toolChangeRectangle)
b.pack( fill = X)
toolbarButtons["rectangle"] = b


b = Button(toolbarframe,text="circ.", font=f, command=toolChangeCircle,relief="sunken")
b.pack(fill = X)
toolbarButtons["circle"] = b


s = ttk.Separator(toolbarframe, orient='horizontal')
s.pack(fill='x', pady=3)


w = Scale(toolbarframe, from_=8, to=512, command=brushSizeSliderChanged)
w.set(32)
w.pack()


toolbarframe.pack( side = LEFT, fill = Y )


imageframe = Frame(window)


paintWindow = PaintWindow(imageframe)



	
#image_container = canvas.create_image(0,0,image=None, anchor="nw")



imageframe.pack( side = TOP, fill = BOTH ,expand=1 )




window.mainloop()
