# $Id$
##
##  This file is part of pyFormex 0.8.6  (Mon Jan 16 21:15:46 CET 2012)
##  pyFormex is a tool for generating, manipulating and transforming 3D
##  geometrical models by sequences of mathematical operations.
##  Home page: http://pyformex.org
##  Project page:  http://savannah.nongnu.org/projects/pyformex/
##  Copyright 2004-2011 (C) Benedict Verhegghe (benedict.verhegghe@ugent.be) 
##  Distributed under the GNU General Public License version 3 or later.
##
##
##  This program is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program.  If not, see http://www.gnu.org/licenses/.
##
"""Graphical User Interface for pyFormex."""

import pyformex as pf
from pyformex.gui import signals

import sys,utils
if not ( utils.hasModule('numpy') and
         utils.hasModule('pyopengl') and
         utils.hasModule('pyqt4') ):
    sys.exit()

import os.path

from PyQt4 import QtCore, QtGui

import menu
import cameraMenu
import fileMenu
import scriptMenu
import appMenu
import prefMenu
import toolbar
import canvas
import viewport

import script
import draw
import widgets
import drawlock
import camera

import warnings

import guifunc


############### General Qt utility functions #######

## might go to a qtutils module

def Size(widget):
    """Return the size of a widget as a tuple."""
    s = widget.size()
    return s.width(),s.height()

def Pos(widget):
    """Return the position of a widget as a tuple."""
    p = widget.pos()
    return p.x(),p.y()

def MaxSize(*args):
    """Return the maximum of a list of sizes"""
    return max([i[0] for i in args]),max([i[1] for i in args])

def MinSize(*args):
    """Return the maximum of a list of sizes"""
    return min([i[0] for i in args]),min([i[1] for i in args])

def printpos(w,t=None):
    print("%s %s x %s" % (t,w.x(),w.y()))
def printsize(w,t=None):
    print("%s %s x %s" % (t,w.width(),w.height()))

################# Message Board ###############

class Board(QtGui.QTextEdit):
    """Message board for displaying read-only plain text messages."""
    
    def __init__(self,parent=None):
        """Construct the Message Board widget."""
        QtGui.QTextEdit.__init__(self,parent)
        self.setReadOnly(True) 
        self.setAcceptRichText(False)
        self.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Sunken)
        self.setMinimumSize(24,24)
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        self.cursor = self.textCursor()
        #self.buffer = ''
        font = QtGui.QFont("DejaVu Sans Mono")
        #font.setStyle(QtGui.QFont.StyleNormal)
        self.setFont(font)
        

    def write(self,s):
        """Write a string to the message board."""
        # A single blank character seems to be generated by a print
        # instruction containing a comma: skip it
        if s == ' ':
            return
        #self.buffer += '[%s:%s]' % (len(s),s)
        s = s.rstrip('\n')
        if len(s) > 0:
            self.append(s)
            self.cursor.movePosition(QtGui.QTextCursor.End)
            self.setTextCursor(self.cursor)


    def save(self,filename):
        """Save the contents of the board to a file"""
        fil = open(filename,'w')
        fil.write(self.toPlainText())
        fil.close()
        

    def flush(self):
        self.update()


#####################################
################# GUI ###############
#####################################


class Gui(QtGui.QMainWindow):
    """Implements a GUI for pyformex."""

    toolbar_area = { 'top': QtCore.Qt.TopToolBarArea,
                     'bottom': QtCore.Qt.BottomToolBarArea,
                     'left': QtCore.Qt.LeftToolBarArea,
                     'right': QtCore.Qt.RightToolBarArea,
                     }

    def __init__(self,windowname,size=(800,600),pos=(0,0),bdsize=(0,0)):
        """Constructs the GUI.

        The GUI has a central canvas for drawing, a menubar and a toolbar
        on top, and a statusbar at the bottom.
        """
        self.on_exit = [fileMenu.askCloseProject] 
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle(windowname)
        # add widgets to the main window


        # The status bar
        self.statusbar = self.statusBar()
        self.curproj = widgets.ButtonBox('Project:',[('None',fileMenu.openProject)])
        self.curfile = widgets.ButtonBox('Script:',[('None',fileMenu.openScript)])
        self.curdir = widgets.ButtonBox('Cwd:',[('None',draw.askDirname)])
        self.canPlay = False
        
        # The menu bar
        self.menu = menu.MenuBar('TopMenu')
        self.setMenuBar(self.menu)

        # The toolbar
        self.toolbar = self.addToolBar('Top ToolBar')
        self.editor = None
        # Create a box for the central widget
        self.box = QtGui.QWidget()
        self.setCentralWidget(self.box)
        self.boxlayout = QtGui.QVBoxLayout()
        self.box.setLayout(self.boxlayout)
        #self.box.setFrameStyle(qt.QFrame.Sunken | qt.QFrame.Panel)
        #self.box.setLineWidth(2)
        # Create a splitter
        self.splitter = QtGui.QSplitter()
        self.boxlayout.addWidget(self.splitter)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.show()

        # self.central is the complete central widget of the main window
        self.central = QtGui.QWidget()
        self.central.autoFillBackground()
          #self.central.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Sunken)
        self.central.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,QtGui.QSizePolicy.MinimumExpanding)
        self.central.resize(*pf.cfg['gui/size'])

        self.viewports = viewport.MultiCanvas(parent=self.central)
        self.central.setLayout(self.viewports)

        # Create the message board
        self.board = Board()
        #self.board.setPlainText(pf.Version+' started')
        # Put everything together
        self.splitter.addWidget(self.central)
        self.splitter.addWidget(self.board)
        #self.splitter.setSizes([(800,200),(800,600)])
        self.box.setLayout(self.boxlayout)
        # Create the top menu
        menudata = menu.createMenuData()
        self.menu.insertItems(menudata)
        # ... and the toolbar
        self.actions = toolbar.addActionButtons(self.toolbar)

        # timeout button 
        toolbar.addTimeoutButton(self.toolbar)

        self.menu.show()

        # Define Toolbars
    
        self.camerabar = self.updateToolBar('camerabar','Camera ToolBar')
        self.modebar = self.updateToolBar('modebar','RenderMode ToolBar')
        self.viewbar = self.updateToolBar('viewbar','Views ToolBar')
        self.toolbars = [self.camerabar, self.modebar, self.viewbar]
        
        ###############  CAMERA menu and toolbar #############
        if self.camerabar:
            toolbar.addCameraButtons(self.camerabar)
            toolbar.addPerspectiveButton(self.camerabar)

        ###############  RENDERMODE menu and toolbar #############
        modes = [ 'wireframe', 'smooth', 'smoothwire', 'flat', 'flatwire' ]
        if pf.cfg['gui/modemenu']:
            mmenu = QtGui.QMenu('Render Mode')
        else:
            mmenu = None
            
        #menutext = '&' + name.capitalize()
        self.modebtns = menu.ActionList(
            modes,guifunc.renderMode,menu=mmenu,toolbar=self.modebar)
        
        # Add the toggle type buttons
        if self.modebar:
            toolbar.addTransparencyButton(self.modebar)
        if self.modebar and pf.cfg['gui/lightbutton']:
            toolbar.addLightButton(self.modebar)
        if self.modebar and pf.cfg['gui/normalsbutton']:
            toolbar.addNormalsButton(self.modebar)
        if self.modebar and pf.cfg['gui/shrinkbutton']:
            toolbar.addShrinkButton(self.modebar)
         
        if mmenu:
            # insert the mode menu in the viewport menu
            pmenu = self.menu.item('viewport')
            pmenu.insertMenu(pmenu.item('background color'),mmenu)

        ###############  VIEWS menu ################
        if pf.cfg['gui/viewmenu']:
            if pf.cfg['gui/viewmenu'] == 'main':
                parent = self.menu
                before = 'help'
            else:
                parent = self.menu.item('camera')
                before = parent.item('---')
            self.viewsMenu = menu.Menu('&Views',parent=parent,before=before)
        else:
            self.viewsMenu = None

        defviews = pf.cfg['gui/defviews']
        views = [ v[0] for v in defviews ]
        viewicons = [ v[1] for v in defviews ]

        self.viewbtns = menu.ActionList(
            views,self.setView,
            menu=self.viewsMenu,
            toolbar=self.viewbar,
            icons = viewicons
            )

        ## TESTING SAVE CURRENT VIEW ##

        self.saved_views = {}
        self.saved_views_name = utils.NameSequence('View')
            
        if self.viewsMenu:
            name = self.saved_views_name.next()
            self.menu.item('camera').addAction('Save View',self.saveView)


        # Restore previous pos/size
        self.resize(*size)
        self.move(*pos)
        self.board.resize(*bdsize)

        app = pf.cfg['curfile']
        if not (app.endswith('.py') or app.endswith('.pye')):
            import apps
            app = app.replace('apps.','')
            app = apps.load(app)
        self.setcurfile(app)
        self.setcurdir()
        if pf.options.redirect:
            sys.stderr = self.board
            sys.stdout = self.board

        if pf.options.debug:
            printsize(self,'DEBUG: Main:')
            printsize(self.central,'DEBUG: Canvas:')
            printsize(self.board,'DEBUG: Board:')

        # Drawing lock
        self.drawwait = pf.cfg['draw/wait']
        self.drawlock = drawlock.DrawLock()

        # Materials and Lights database
        self.materials = canvas.createMaterials()
        ## for m in self.materials:
        ##     print self.materials[m]


    def saveView(self,name=None,addtogui=True):
        """Save the current view and optionally create a button for it.

        This saves the current viewport ModelView and Projection matrices
        under the specified name.

        It adds the view to the views Menu and Toolbar, if these exist and
        do not have the name yet.
        """
        if name is None:
            name = self.saved_views_name.next()
        self.saved_views[name] = (pf.canvas.camera.m,None)
        if name not in self.viewbtns.names():
            iconpath = os.path.join(pf.cfg['icondir'],'userview')+pf.cfg['gui/icontype']
            self.viewbtns.add(name,iconpath)


    def applyView(self,name):
        """Apply a saved view to the current camera.

        """
        m,p = self.saved_views.get(name,(None,None))
        if m is not None:
            self.viewports.current.camera.loadModelView(m)


    def createView(self,name,angles):
        """Create a new view and add it to the list of predefined views.

        This creates a named view with specified angles or, if the name
        already exists, changes its angles to the new values.

        It adds the view to the views Menu and Toolbar, if these exist and
        do not have the name yet.
        """
        if name not in self.viewbtns.names():
            iconpath = os.path.join(pf.cfg['icondir'],'userview')+pf.cfg['gui/icontype']
            self.viewbtns.add(name,iconpath)
        camera.view_angles[name] = angles


    def setView(self,view):
        """Change the view of the current GUI viewport, keeping the bbox.

        view is the name of one of the defined views.
        """
        if view in self.saved_views:
            self.applyView(view)
        else:
            self.viewports.current.setCamera(angles=view)
        self.viewports.current.update()
 

    def updateToolBars(self):
        for t in ['camerabar','modebar','viewbar']:
            self.updateToolBar(t)

    def updateToolBar(self,shortname,fullname=None):
        """Add a toolbar or change its position.

        This function adds a toolbar to the GUI main window at the position
        specified in the configuration. If the toolbar already exists, it is
        moved from its previous location to the requested position. If the
        toolbar does not exist, it is created with the given fullname, or the
        shortname by default.

        The full name is the name as displayed to the user.
        The short name is the name as used in the config settings.

        The config setting for the toolbar determines its placement:
        - None: the toolbar is not created
        - 'left', 'right', 'top' or 'bottom': a separate toolbar is created
        - 'default': the default top toolbar is used and a separator is added.
        """
        area = pf.cfg['gui/%s' % shortname]
        try:
            toolbar = getattr(self,shortname)
        except:
            toolbar = None
            
        if area:
            area = self.toolbar_area.get(area,4) # default is top
            # Add/reposition the toolbar
            if toolbar is None:
                if fullname is None:
                    fullname = shortname
                toolbar = QtGui.QToolBar(fullname,self)
            self.addToolBar(area,toolbar)
        else:
            if toolbar is not None:
                self.removeToolBar(toolbar)
                toolbar = None
            
        return toolbar
 

    ## def activateToolBar(self,fullname,shortname):
    ##     """Add a new toolbar to the GUI main window.

    ##     The full name is the name as displayed to the user.
    ##     The short name is the name as used in the config settings.

    ##     The config setting for the toolbar determines its placement:
    ##     - None: the toolbar is not created
    ##     - 'left', 'right', 'top' or 'bottom': a separate toolbar is created
    ##     - 'default': the default top toolbar is used and a separator is added.
    ##     """
    ##     area = pf.cfg['gui/%s' % shortname]
    ##     if area:
    ##         area = self.toolbar_area.get(area,0)
    ##         if area:
    ##             toolbar = QtGui.QToolBar(fullname,self)
    ##             self.addToolBar(area,toolbar)
    ##         else: # default
    ##             toolbar = self.toolbar
    ##             self.toolbar.addSeparator()
    ##     else:
    ##         toolbar = None
    ##     return toolbar


    def addStatusBarButtons(self):
        sbh = self.statusbar.height()
        #self.curproj.setFixedHeight(32)
        #self.curfile.setFixedHeight(32)
        self.statusbar.addWidget(self.curproj)
        self.statusbar.addWidget(self.curfile)
        self.statusbar.addWidget(self.curdir)


    def addInputBox(self):
        self.input = widgets.InputString('Input:','')
        self.statusbar.addWidget(self.input)


    def toggleInputBox(self,onoff=None):
        if onoff is None:
            onoff = self.input.isHidden()
        self.input.setVisible(onoff)


    def addCoordsTracker(self):
        self.coordsbox = widgets.CoordsBox()
        self.statusbar.addPermanentWidget(self.coordsbox)

        
    def toggleCoordsTracker(self,onoff=None):
        def track(x,y,z):
            X,Y,Z = pf.canvas.unProject(x,y,z,True)
            print "%s --> %s" % ((x,y,z),(X,Y,Z))
            pf.GUI.coordsbox.setValues([X,Y,Z])

        if onoff is None:
            onoff = self.coordsbox.isHidden()
        if onoff:
            func = track
        else:
            func = None
        for vp in self.viewports.all:
            vp.trackfunc = func
        self.coordsbox.setVisible(onoff)
         
    
    def resizeCanvas(self,wd,ht):
        """Resize the canvas."""
        self.central.resize(wd,ht)
        self.box.resize(wd,ht+self.board.height())
        self.adjustSize()
        print("RESIZED",Pos(self))
    
    def showEditor(self):
        """Start the editor."""
        if not hasattr(self,'editor'):
            self.editor = Editor(self,'Editor')
            self.editor.show()
            self.editor.setText("Hallo\n")

    def closeEditor(self):
        """Close the editor."""
        if hasattr(self,'editor'):
            self.editor.close()
            self.editor = None
    

    def setcurproj(self,project=''):
        """Show the current project name."""
        if project:
            project = os.path.basename(project)
        self.curproj.setText(project)


    def setcurfile(self,app):
        """Set the current script or application.

        app is either an imported application module, an application
        module name or a script file.
        """
        from types import ModuleType
        is_app = type(app) is ModuleType
        if is_app:
            name = app.__name__.replace('apps.','')
            self.canPlay = hasattr(app,'run')
            self.curfile.label.setText('App:')
            if 'ReRun' in self.actions:
                self.actions['ReRun'].setEnabled(self.canPlay)
            pf.prefcfg['curfile'] = name
        else:
            name = os.path.basename(app)
            self.canPlay = utils.is_pyFormex(app) or app.endswith('.pye')
            self.curfile.label.setText('Script:')
            if 'Step' in self.actions:
                self.actions['Step'].setEnabled(self.canPlay)
            pf.prefcfg['curfile'] = app

        self.curfile.setText(name)
        self.actions['Play'].setEnabled(self.canPlay)
        self.actions['Stop'].setEnabled(self.canPlay)
        icon = 'ok' if self.canPlay else 'notok'
        self.curfile.setIcon(QtGui.QIcon(QtGui.QPixmap(os.path.join(pf.cfg['icondir'],icon)+pf.cfg['gui/icontype'])),0)


    def setcurdir(self):
        """Show the current workdir."""
        dirname = os.getcwd()
        shortname = os.path.basename(dirname)
        self.curdir.setText(shortname)
        self.curdir.setToolTip(dirname)


    def setBusy(self,busy=True,force=False):
        if busy:
            pf.app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        else:
            pf.app.restoreOverrideCursor()
        self.processEvents()


    def resetCursor(self):
        """Clear the override cursor stack.

        This will reset the application cursor to the initial default.
        """
        while pf.app.overrideCursor():
            pf.app.restoreOverrideCursor()
        self.processEvents()
    


    def keyPressEvent(self,e):
        """Top level key press event handler.

        Events get here if they are not handled by a lower level handler.
        Every key press arriving here generates a WAKEUP signal, and if a
        dedicated signal for the key was installed in the keypress table,
        that signal is emitted too.
        Finally, the event is removed.
        """
        key = e.key()
        pf.debug('Key %s pressed' % key)
        self.emit(signals.WAKEUP,())
        signal = signals.keypress_signal.get(key,None)
        if signal:
            self.emit(signal,())
        e.ignore()


    def XPos(self):
        """Get the main window position from the xwininfo command.

        The (Py)Qt4 position does not get updated when
        changing the window size from the left.
        This substitute function will find the correct position from
        the xwininfo command output.
        """
        res = xwininfo(self.winId())
        ax,ay,rx,ry = [ int(res[key]) for key in [
            'Absolute upper-left X','Absolute upper-left Y',
            'Relative upper-left X','Relative upper-left Y',
            ]]
        return ax-rx,ay-ry


    def writeSettings(self):
        """Store the GUI settings"""
        # FIX QT4 BUG
        # Make sure QT4 has position right
        self.move(*self.XPos())

        # store the history and main window size/pos
        pf.prefcfg['gui/history'] = pf.GUI.history.files

        pf.prefcfg.update({'size':Size(pf.GUI),
                           'pos':Pos(pf.GUI),
                           'bdsize':Size(pf.GUI.board),
                           },name='gui')


    def cleanup(self):
        """Cleanup the GUI (restore default state)."""
        pf.debug('GUI cleanup')
        self.drawlock.release()
        pf.canvas.cancel_selection()
        pf.canvas.cancel_draw()
        draw.clear_canvas()
        self.setBusy(False)


    def closeEvent(self,event):
        """Close Main Window Event Handler"""
##         if draw.ack("Do you really want to quit?"):
##             print("YES:EXIT")
        self.cleanup()
        pf.debug("Executing registered exit functions")
        for f in self.on_exit:
            pf.debug(f)
            f()
        self.writeSettings()
        event.accept()
##         else:
##             print("NO:STAY")
##             event.ignore()

    def onExit(self,func):
        """Register a function for execution on exit"""
        self.on_exit.append(func)
            
# THESE FUNCTION SHOULD BECOME app FUNCTIONS

    def currentStyle(self):
        return pf.app.style().metaObject().className()[1:-5]


    def getStyles(self):
        return map(str,QtGui.QStyleFactory().keys())


    def setStyle(self,style):
        """Set the main application style."""
        style = QtGui.QStyleFactory().create(style)
        pf.app.setStyle(style)
        self.update()


    def setFont(self,font):
        """Set the main application font.

        font is either a QFont or a string resulting from the
        QFont.toString() method
        """
        if not isinstance(font,QtGui.QFont):
            f = QtGui.QFont()
            f.fromString(font)
            font = f
        pf.app.setFont(font)
        self.update()


    def setFontFamily(self,family):
        """Set the main application font family to the given family."""
        font = pf.app.font()
        font.setFamily(family)
        self.setFont(font)


    def setFontSize(self,size):
        """Set the main application font size to the given point size."""
        font = pf.app.font()
        font.setPointSize(int(size))
        self.setFont(font)


    def setAppearence(self):
        """Set all the GUI appearence elements.

        Sets the GUI appearence from the current configuration values
        'gui/style', 'gui/font', 'gui/fontfamily', 'gui/fontsize'.
        """
        style = pf.cfg['gui/style']
        font = pf.cfg['gui/font']
        family = pf.cfg['gui/fontfamily']
        size = pf.cfg['gui/fontsize']
        if style:
            self.setStyle(style)
        if font:
            self.setFont(font)
        if family:
            self.setFontFamily(family)
        if size:
            self.setFontSize(size)


    def processEvents(self):
        """Process interactive GUI events."""
        #saved = pf.canvas
        #print "SAVED script canvas %s" % pf.canvas
        #pf.canvas = self.viewports.current
        #print "SET script canvas %s" % pf.canvas
        if pf.app:
            pf.app.processEvents()
        #pf.canvas = saved
        #print "RESTORED script canvas %s" % pf.canvas


    def findDialog(self,name):
        """Find the InputDialog with the specified name.

        Returns the list with maching dialogs, possibly empty.
        """
        return self.findChildren(widgets.InputDialog,str(name))


    def closeDialog(self,name):
        """Close the InputDialog with the specified name.

        Closest all the InputDialogs with the specified caption
        owned by the GUI.
        """
        for w in self.findDialog(name):
            w.close()


def xwininfo(windowid=None,name=None):
    """Returns the X window info parsed as a dict.

    Either the windowid or the window name has to be specified.
    """
    import re
    cmd = 'xwininfo %s 2> /dev/null'
    if windowid is not None:
        args = " -id %s" % windowid
    elif name is not None:
        args = " -name '%s'" % name
    else:
        raise ValueError,"Either windowid or name have to be specified"

    sta,out = utils.runCommand(cmd % args,RaiseError=False,quiet=True)
    res = {}
    if not sta:
        for line in out.split('\n'):
            s = line.split(':')
            if len(s) < 2:
                s = s[0].strip().split(' ')
            if len(s) < 2:
                continue
            elif len(s) > 2:
                if s[0] == 'xwininfo':
                    s = s[-2:] # remove the xwininfo string
                    t = s[1].split()
                    s[1] = t[0] # windowid
                    name = ' '.join(t[1:]).strip().strip('"')
                    res['Window name'] = name
            if s[0][0] == '-':
                s[0] = s[0][1:]
            res[s[0].strip()] = s[1].strip()

    return res


def pidofxwin(windowid):
    """Returns the PID of the process that has created the window.

    Remark: Not all processes store the PID information in the way
    it is retrieved here. In many cases (X over network) the PID can
    not be retrieved. However, the intent of this function is just to
    find a dangling pyFormex process, and should probably work on
    a normal desktop configuration.
    """
    import re
    sta,out = utils.runCommand('xprop -id %s _NET_WM_PID' % windowid,quiet=True)
    m = re.match("_NET_WM_PID\(.*\)\s*=\s*(?P<pid>\d+)",out)
    if m:
        pid = m.group('pid')
        #print "Found PID %s" % pid
        return int(pid)
    
    return None


def windowExists(windowname):
    """Check if a GUI window with the given name exists.

    On X-Window systems, we can use the xwininfo command to find out whether
    a window with the specified name exists.
    """
    return not os.system('xwininfo -name "%s" > /dev/null 2>&1' % windowname)


def findOldProcesses(max=16):
    """Find old pyFormex GUI processes still running.

    There is a maximum to the number of processes taht can be detected.
    16 will suffice laregley, because there is no sane reason to open that many
    pyFormex GUI's on the same screen.

    Returns the next available main window name, and a list of
    running pyFormex GUI processes, if any.
    """
    windowname = pf.Version
    count = 0
    running = []

    while count < max:
        info = xwininfo(name=windowname)
        if info:
            name = info['Window name']
            windowid = info['Window id']
            if name == windowname:
                pid = pidofxwin(windowid)
            else:
                pid = None
            # pid control needed for invisible windows on ubuntu
            if pid:
                running.append((windowid,name,pid))
                count += 1
                windowname = '%s (%s)' % (pf.Version,count)
            else:
                break
        else:
            break 

    return windowname,running
        

def killProcesses(pids):
    """Kill the processes in the pids list."""
    warning = """..

Killing processes
-----------------
I will now try to kill the following processes::

    %s

You can choose the signal to be sent to the processes:

- KILL (9)
- TERM (15)

We advice you to first try the TERM(15) signal, and only if that
does not seem to work, use the KILL(9) signal.
""" % pids
    actions = ['Cancel the operation','KILL(9)','TERM(15)']
    answer = draw.ask(warning,actions)
    if answer == 'TERM(15)':
        utils.killProcesses(pids,15)
    elif answer == 'KILL(9)':
        utils.killProcesses(pids,9)



def quitGUI():
    """Quit the GUI"""
    pf.debug("Quit GUI")
    sys.stderr = sys.__stderr__
    sys.stdout = sys.__stdout__
    #print "QUIT"
    pf.GUI.drawlock.free()
    draw.wakeup()
    if pf.options.gui:
        script.force_finish()
    if pf.app:
        pf.app.exit()
        pf.app = None


def startGUI(args):
    """Create the QT4 application and GUI.

    A (possibly empty) list of command line options should be provided.
    QT4 wil remove the recognized QT4 and X11 options.
    """
    # This seems to be the only way to make sure the numeric conversion is
    # always correct
    #
    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    #
    #pf.options.debug = -1
    pf.debug("Arguments passed to the QApplication: %s" % args)
    pf.app = QtGui.QApplication(args)
    #
    pf.debug("Arguments left after constructing the QApplication: %s" % args)
    pf.debug("Arguments left after constructing the QApplication: %s" % pf.app.arguments().join('\n'))
    #pf.options.debug = 0
    # As far as I have been testing this, the args passed to the Qt application are
    # NOT acknowledged and neither are they removed!!


    pf.debug("Setting application attributes")
    pf.app.setOrganizationName("pyformex.org")
    pf.app.setOrganizationDomain("pyformex.org")
    pf.app.setApplicationName("pyFormex")
    pf.app.setApplicationVersion(pf.__version__)
    ## pf.settings = QtCore.QSettings("pyformex.org", "pyFormex")
    ## pf.settings.setValue("testje","testvalue")
    
    #QtCore.QObject.connect(pf.app,QtCore.SIGNAL("lastWindowClosed()"),pf.app,QtCore.SLOT("quit()"))
    QtCore.QObject.connect(pf.app,QtCore.SIGNAL("lastWindowClosed()"),quitGUI)
    #QtCore.QObject.connect(pf.app,QtCore.SIGNAL("aboutToQuit()"),quitGUI)

    # Check if we have DRI
    pf.debug("Setting OpenGL format")
    viewport.setOpenGLFormat()
    dri = viewport.opengl_format.directRendering()


    # Check for existing pyFormex processes
    pf.debug("Checking for running pyFormex")
    if pf.X11:
        windowname,running = findOldProcesses()
    else:
        windowname,running = "UNKOWN",[]
    pf.debug("%s,%s" % (windowname,running))
    
    
    while len(running) > 0:
        if len(running) >= 16:
            print("Too many open pyFormex windows --- bailing out")
            return -1

        pids = [ i[2] for i in running if i[2] is not None ]
        warning = """..

pyFormex is already running on this screen
------------------------------------------
A main pyFormex window already exists on your screen. 

If you really intended to start another instance of pyFormex, you
can just continue now.

The window might however be a leftover from a previously crashed pyFormex
session, in which case you might not even see the window anymore, nor be able
to shut down that running process. In that case, you would better bail out now
and try to fix the problem by killing the related process(es).

If you think you have already killed those processes, you may check it by
rerunning the tests.
"""
        actions = ['Really Continue','Rerun the tests','Bail out and fix the problem']
        if pids:
            warning += """

I have identified the process(es) by their PID as::

%s

If you trust me enough, you can also have me kill this processes for you.
""" % pids
            actions[2:2] = ['Kill the running processes']
            
        if dri:
            answer = draw.ask(warning,actions)
        else:
            warning += """
I have detected that the Direct Rendering Infrastructure
is not activated on your system. Continuing with a second
instance of pyFormex may crash your XWindow system.
You should seriously consider to bail out now!!!
"""
            answer = draw.warning(warning,actions)


        if answer == 'Really Continue':
            break # OK, Go ahead

        elif answer == 'Rerun the tests':
            windowname,running = findOldProcesses() # try again
        
        elif answer == 'Kill the running processes':
            killProcesses(pids)
            windowname,running = findOldProcesses() # try again
            
        else:
            return -1 # I'm out of here!

        
    # Load the splash image
    pf.debug("Loading the splash image")
    splash = None
    if os.path.exists(pf.cfg['gui/splash']):
        pf.debug('Loading splash %s' % pf.cfg['gui/splash'])
        splashimage = QtGui.QPixmap(pf.cfg['gui/splash'])
        splash = QtGui.QSplashScreen(splashimage)
        splash.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        splash.setFont(QtGui.QFont("Helvetica",24))
        splash.showMessage(pf.Version,QtCore.Qt.AlignHCenter,QtCore.Qt.red)
        splash.show()

    # create GUI, show it, run it

    pf.debug("Creating the GUI")
    desktop = pf.app.desktop()
    pf.maxsize = Size(desktop.availableGeometry())
    size = pf.cfg.get('gui/size',(800,600))
    pos = pf.cfg.get('gui/pos',(0,0))
    bdsize = pf.cfg.get('gui/bdsize',(800,600))
    size = MinSize(size,pf.maxsize)
    pf.GUI = Gui(windowname,
                 pf.cfg.get('gui/size',(800,600)),
                 pf.cfg.get('gui/pos',(0,0)),
                 pf.cfg.get('gui/bdsize',(800,600)),
                 )

    # set the appearance
    pf.GUI.setAppearence()


    # setup the message board
    pf.board = pf.GUI.board
    pf.board.write("""%s  (Rev. %s)   (C) Benedict Verhegghe

pyFormex comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it under the conditions of the GNU General Public License, version 3 or later. See Help->License or the file COPYING for details.
""" % (pf.Version,pf.__revision__))

    # Set interaction functions
    
    def show_warning(message,category,filename,lineno,file=None,line=None):
        """Replace the default warnings.showwarning

        We display the warnings using our interactive warning widget.
        This feature can be turned off by setting
        cfg['warnings/popup'] = False
        """
        full_message = warnings.formatwarning(message,category,filename,lineno,line)
        ## from widgets import simpleInputItem as I
        ## res = draw.askItems([
        ##     I('message',message,itemtype='label',text='warning'),
        ##     I('filter',False,text='Suppress this message in future sessions'),
        ##     ],actions=[('OK',)],legacy=False)
        #print res
        pf.message(full_message)
        res,check = draw.showMessage(full_message,level='warning',check="Do not show this warning anymore in future sessions")
        if check[0]:
            oldfilters = pf.prefcfg['warnings/filters']
            newfilters = oldfilters + [(str(message),)]
            pf.prefcfg.update({'filters':newfilters},name='warnings')


##     def format_warning(message,category,filename,lineno,line=None):
##         """Replace the default warnings.formatwarning

##         We display the warnings using our interactive warning widget.
##         This feature can be turned off by setting
##         cfg['nice_warnings'] = False
##         """
##         import messages
##         message = messages.getMessage(message)
##         message = """..

## pyFormex Warning
## ================
## %s

## `Called from:` %s `line:` %s
## """ % (message,filename,lineno)
##         if line:
##             message += "%s\n" % line
##         return message


##     if pf.cfg['warnings/nice']:
##         warnings.formatwarning = format_warning

    if pf.cfg['warnings/popup']:
        warnings.showwarning = show_warning
    
    
    pf.message = draw.message
    pf.warning = draw.warning

    # setup the canvas
    pf.GUI.viewports.changeLayout(1)
    pf.GUI.viewports.setCurrent(0)
    pf.canvas = pf.GUI.viewports.current
    draw.reset()

    # setup the status bar
    pf.GUI.addInputBox()
    pf.GUI.toggleInputBox(False)
    pf.GUI.addCoordsTracker()
    pf.GUI.toggleCoordsTracker(pf.cfg.get('gui/coordsbox',False))
    pf.debug("Using window name %s" % pf.GUI.windowTitle())
    
    # Create additional menus (put them in a list to save)
    
    # History Menu
    pf.GUI.history = scriptMenu.ScriptMenu('History',files=pf.cfg['gui/history'],max=pf.cfg['gui/history_max'])

    if pf.cfg.get('gui/history_in_main_menu',False):
        before = pf.GUI.menu.item('help')
        pf.GUI.menu.insertMenu(before,pf.GUI.history)
    else:
        filemenu = pf.GUI.menu.item('file')
        before = filemenu.item('---1')
        filemenu.insertMenu(before,pf.GUI.history)
    

    # Scripts menu
    pf.GUI.scriptmenu = scriptMenu.createScriptMenu(pf.GUI.menu,before='help')
   

    # App menu
    pf.GUI.appmenu = appMenu.createMenu(pf.GUI.menu,before='help')

    # Create databases
    createDatabases()
 
    # Plugin menus
    import plugins
    filemenu = pf.GUI.menu.item('file')
    pf.gui.plugin_menu = plugins.create_plugin_menu(filemenu,before='History')
    # Load configured plugins, ignore if not found
    plugins.loadConfiguredPlugins()

    ## Now have their top menu
    ## # Applications 
    ## try:
    ##     import apps
    ##     pf.apps = apps._available_apps
    ##     print "Applications: "+ ', '.join(pf.apps)
    ##     appmenu = pf.GUI.menu.item('file')
    ##     pf.gui.app_menu = appMenu.create_app_menu(filemenu,before='History')
    ## except:
    ##     print "No applications available"
    ##     raise
        
    # Last minute menu modifications can go here
        


    # cleanup
    pf.GUI.setBusy(False)         # HERE
    pf.GUI.addStatusBarButtons()

    if splash is not None:
        # remove the splash window
        splash.finish(pf.GUI)

    pf.GUI.setBusy(False)        # OR HERE

    pf.debug("Showing the GUI")
    pf.GUI.show()
    pf.GUI.update()

    if pf.cfg['gui/fortune']:
        sta,out = utils.runCommand(pf.cfg['fortune'])
        if sta == 0:
            draw.showInfo(out)


    warnings.warn('warn_quadratic_drawing')

    pf.app_started = True
    pf.GUI.processEvents()
    return 0


def createDatabases():
    """Create unified database objects for all menus."""
    from plugins import objects
    from geometry import Geometry
    from formex import Formex
    from mesh import Mesh
    from plugins.trisurface import TriSurface
    from plugins.curve import PolyLine,BezierSpline
    from plugins.nurbs import NurbsCurve
    pf.GUI.database = objects.Objects()
    pf.GUI.drawable = objects.DrawableObjects()
    pf.GUI.selection = {
        'geometry' : objects.DrawableObjects(clas=Geometry),
        'formex' : objects.DrawableObjects(clas=Formex),
        'mesh' : objects.DrawableObjects(clas=Mesh),
        'surface' : objects.DrawableObjects(clas=TriSurface),
        'polyline' : objects.DrawableObjects(clas=PolyLine),
        'nurbs' : objects.DrawableObjects(clas=NurbsCurve),
        'curve' : objects.DrawableObjects(clas=BezierSpline),
        }

def runGUI():
    """Go into interactive mode"""
    
    egg = pf.cfg.get('gui/easter_egg',None)
    pf.debug('EGG: %s' % str(egg))
    if egg:
        pf.debug('EGG')
        if type(egg) is str:
            pye = egg.endswith('pye')
            egg = open(egg).read()
        else:
            pye = True
            egg = ''.join(egg)
        draw.playScript(egg,pye=True)

    if os.path.isdir(pf.cfg['workdir']):
        # Make the workdir the current dir
        os.chdir(pf.cfg['workdir'])
        pf.debug("Setting workdir to %s" % pf.cfg['workdir'])
    else:
        # Save the current dir as workdir
        prefMenu.updateSettings({'workdir':os.getcwd(),'Save changes':True})

    pf.interactive = True
    pf.debug("Start main loop")

    #utils.procInfo('runGUI')
    #from multiprocessing import Process
    #p = Process(target=pf.app.exec_)
    #p.start()
    #res = p.join()
    res = pf.app.exec_()
    pf.debug("Exit main loop with value %s" % res)
    return res


def classify_examples():
    m = pf.GUI.menu.item('Examples')
        


#### End
