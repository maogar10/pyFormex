# canvas.py
# $Id$
##
## This file is part of pyFormex 0.4.2 Release Mon Feb 26 08:57:40 2007
## pyFormex is a python implementation of Formex algebra
## Homepage: http://pyformex.berlios.de/
## Distributed under the GNU General Public License, see file COPYING
## Copyright (C) Benedict Verhegghe except where stated otherwise 
##
"""This implements an OpenGL drawing widget for painting 3D scenes."""

import globaldata as GD

from numpy import *
from OpenGL import GL,GLU

from formex import length
import colors
import camera
import actors
import decors
import marks
import utils


class ActorList(list):

    def __init__(self,canvas,useDisplayLists=True):
        self.canvas = canvas
        self.uselists = useDisplayLists
        list.__init__(self)
        
    def add(self,actor):
        """Add an actor to an actorlist."""
        if self.uselists:
            self.canvas.makeCurrent()
            actor.list = GL.glGenLists(1)
            GL.glNewList(actor.list,GL.GL_COMPILE)
            actor.draw(self.canvas.rendermode)
            GL.glEndList()
        self.append(actor)

    def delete(self,actor):
        """Remove an actor from an actorlist."""
        if actor in self:
            self.remove(actor)
            if self.uselists and actor.list:
                self.canvas.makeCurrent()
                GL.glDeleteLists(actor.list,1)


    def redraw(self,actorlist=None):
        """Redraw (some) actors in the scene.

        This redraws the specified actors (recreating their display list).
        This should e.g. be used after changing an actor's properties.
        Only actors that are in the current actor list will be redrawn.
        If no actor list is specified, the whole current actorlist is redrawn.
        """
        if actorlist is None:
            actorlist = self
        if self.uselists:
            for actor in actorlist:
                if actor.list:
                    GL.glDeleteLists(actor.list,1)
                actor.list = GL.glGenLists(1)
                GL.glNewList(actor.list,GL.GL_COMPILE)
                actor.draw(self.canvas.rendermode)
                GL.glEndList()

                
##################################################################
#
#  The Canvas
#
class Canvas(object):
    """A canvas for OpenGL rendering."""
    
    # default light
    default_light = { 'ambient':0.5, 'diffuse': 1.0, 'specular':0.5, 'position':(0.,0.,1.,0.)}
    

    def __init__(self):
        """Initialize an empty canvas with default settings."""
        self.actors = ActorList(self)       # start with an empty scene
        self.annotations = ActorList(self)  # without annotations
        self.decorations = ActorList(self)  # and no decorations either
        self.triade = None
        self.lights = []
        self.setBbox()
        self.bgcolor = colors.mediumgrey
        self.fgcolor = colors.black
        self.slcolor = colors.red
        self.rendermode = 'wireframe'
        self.dynamouse = True  # dynamic mouse action works on mouse move
        self.dynamic = None    # what action on mouse move
        self.mousefunc = {}
        self.camera = None
        self.view_angles = camera.view_angles

    
    def addLight(self,position,ambient,diffuse,specular):
        """Adds a new light to the scene."""
        pass
    

    def initCamera(self):
        if GD.options.makecurrent:
            self.makeCurrent()  # we need correct OpenGL context for camera
        self.camera = camera.Camera()
        GD.debug("camera.rot = %s" % self.camera.rot)
        GD.debug("view angles: %s" % self.view_angles)


##    def update(self):
##        GD.app.processEvents()


    def glinit(self,mode=None):
        GD.debug("canvas GLINIT")
        if mode:
            self.rendermode = mode
            
        GL.glClearColor(*colors.RGBA(self.bgcolor))# Clear The Background Color
        GL.glClearDepth(1.0)	       # Enables Clearing Of The Depth Buffer
        GL.glDepthFunc(GL.GL_LESS)	       # The Type Of Depth Test To Do
        GL.glEnable(GL.GL_DEPTH_TEST)	       # Enables Depth Testing
        #GL.glEnable(GL.GL_CULL_FACE)
        #GL.glPolygonMode(GL.GL_FRONT_AND_BACK,GL.GL_LINE) # WIREFRAME!
        

        if self.rendermode == 'wireframe':
            GL.glShadeModel(GL.GL_FLAT)      # Enables Flat Color Shading
            GL.glDisable(GL.GL_LIGHTING)
        elif self.rendermode.startswith('flat'):
            GL.glShadeModel(GL.GL_FLAT)      # Enables Flat Color Shading
            GL.glDisable(GL.GL_LIGHTING)
        elif self.rendermode.startswith('smooth'):
            GL.glShadeModel(GL.GL_SMOOTH)    # Enables Smooth Color Shading
            GL.glEnable(GL.GL_LIGHTING)
            for l,i in zip(['light0','light1'],[GL.GL_LIGHT0,GL.GL_LIGHT1]):
                key = 'render/%s' % l
                light = GD.cfg.get(key,self.default_light)
                GD.debug("  set up %s %s" % (l,light))
                GL.glLightModel(GL.GL_LIGHT_MODEL_AMBIENT,colors.GREY(GD.cfg['render/ambient']))
                GL.glLightModel(GL.GL_LIGHT_MODEL_TWO_SIDE, GL.GL_TRUE)
                GL.glLightModel(GL.GL_LIGHT_MODEL_LOCAL_VIEWER, 0)
                GL.glLightfv(i,GL.GL_AMBIENT,colors.GREY(light['ambient']))
                GL.glLightfv(i,GL.GL_DIFFUSE,colors.GREY(light['diffuse']))
                GL.glLightfv(i,GL.GL_SPECULAR,colors.GREY(light['specular']))
                GL.glLightfv(i,GL.GL_POSITION,colors.GREY(light['position']))
                GL.glEnable(i)
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK,GL.GL_SPECULAR,colors.GREY(GD.cfg['render/specular']))
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK,GL.GL_EMISSION,colors.GREY(GD.cfg['render/emission']))
            GL.glMaterialfv(GL.GL_FRONT_AND_BACK,GL.GL_SHININESS,GD.cfg['render/shininess'])
            GL.glColorMaterial(GL.GL_FRONT_AND_BACK,GL.GL_AMBIENT_AND_DIFFUSE)
            GL.glEnable(GL.GL_COLOR_MATERIAL)
        else:
            raise RuntimeError,"Unknown rendering mode"

    
    def setSize (self,w,h):
        if h == 0:	# Prevent A Divide By Zero 
            h = 1
        GL.glViewport(0, 0, w, h)
        self.aspect = float(w)/h
        self.camera.setLens(aspect=self.aspect)
        self.display()


    def clear(self):
        """Clear the canvas to the background color."""
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glClearColor(*colors.RGBA(self.bgcolor))


    def display(self):
        """(Re)display all the actors in the scene.

        This should e.g. be used when actors are added to the scene,
        or after changing  camera position/orientation or lens.
        """
        self.clear()
        # Draw Scene Actors
        self.camera.loadProjection()
        self.camera.loadMatrix()
        for actor in self.actors:
            GL.glCallList(actor.list)
        for actor in self.annotations:
            GL.glCallList(actor.list)
            #actor.draw()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        # Plot viewport decorations
        GL.glLoadIdentity()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluOrtho2D(0, self.width(), 0, self.height())
        for actor in self.decorations:
            GL.glCallList(actor.list)
        # end plot viewport decorations
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPopMatrix()
##         # Display angles
##         self.camera.getCurrentAngles()
        

    def setLinewidth(self,lw):
        """Set the linewidth for line rendering."""
        GL.glLineWidth(lw)


    def setBgColor(self,bg):
        """Set the background color."""
        self.bgcolor = bg


    def setFgColor(self,fg):
        """Set the default foreground color."""
        self.fgcolor = fg
        GL.glColor3fv(self.fgcolor)

        
    def setBbox(self,bbox=None):
        """Set the bounding box of the scene you want to be visible."""
        # TEST: use last actor
        if bbox is None:
            if len(self.actors) > 0:
                bbox = self.actors[-1].bbox()
            else:
                bbox = [[-1.,-1.,-1.],[1.,1.,1.]]
        self.bbox = asarray(bbox)

         
    def addActor(self,actor):
        """Add a 3D actor to the 3D scene."""
        self.actors.add(actor)

    def removeActor(self,actor):
        """Remove a 3D actor from the 3D scene."""
        self.actors.delete(actor)

         
    def addMark(self,actor):
        """Add an annotation to the 3D scene."""
        self.annotations.add(actor)

    def removeMark(self,actor):
        """Remove an annotation from the 3D scene."""
        self.annotations.delete(actor)

         
    def addDecoration(self,actor):
        """Add a 2D decoration to the canvas."""
        self.decorations.add(actor)

    def removeDecoration(self,actor):
        """Remove a 2D decoration from the canvas."""
        self.decorations.delete(actor)

    def remove(self,itemlist):
        """Remove a list of any actor/annotation/decoration items.

        itemlist can also be a single item instead of a list.
        """
        if not type(itemlist) == list:
            itemlist = [ itemlist ]
        for item in itemlist:
            if isinstance(item,actors.Actor):
                self.actors.delete(item)
            elif isinstance(item,marks.Mark):
                self.annotations.delete(item)
            elif isinstance(item,decors.Decoration):
                self.decorations.delete(item)
        

    def removeActors(self,actorlist=None):
        """Remove all actors in actorlist (default = all) from the scene."""
        if actorlist == None:
            actorlist = self.actors[:]
        for actor in actorlist:
            self.removeActor(actor)
        self.setBbox()


    def removeMarks(self,actorlist=None):
        """Remove all actors in actorlist (default = all) from the scene."""
        if actorlist == None:
            actorlist = self.annotations[:]
        for actor in actorlist:
            self.removeMark(actor)


    def removeDecorations(self,actorlist=None):
        """Remove all decorations in actorlist (default = all) from the scene."""
        if actorlist == None:
            actorlist = self.decorations[:]
        for actor in actorlist:
            self.removeDecoration(actor)


    def removeAll(self):
        """Remove all actors and decorations"""
        self.removeActors()
        self.removeMarks()
        self.removeDecorations()
        self.display()


    def redrawAll(self):
        """Redraw all actors in the scene."""
        self.actors.redraw()
        self.annotations.redraw()
        self.decorations.redraw()
        self.display()

        
##     def setView(self,bbox=None,side=None):
##         """Sets the camera looking from one of the named views."""
## ##         # select view angles: if undefined use (0,0,0)
## ##         if side:
## ##             angles = self.camera.getAngles(side)
## ##         else:
## ##             angles = None
##         self.setCamera(bbox,angles)

        
    def setCamera(self,bbox=None,angles=None):
        """Sets the camera looking under angles at bbox.

        This function sets the camera angles and adjusts the zooming.
        The camera distance remains unchanged.
        If a bbox is specified, the camera will be zoomed to make the whole
        bbox visible.
        If no bbox is specified, the current scene bbox will be used.
        If no current bbox has been set, it will be calculated as the
        bbox of the whole scene.
        """
        self.makeCurrent()
        # go to a distance to have a good view with a 45 degree angle lens
        if not bbox is None:
            self.setBbox(bbox)
        bbox = self.bbox
        center = (bbox[0]+bbox[1]) / 2
        size = bbox[1] - bbox[0]
        # calculating the bounding circle: this is rather conservative
        dist = length(size)
        if dist <= 0.0:
            dist = 1.0
        self.camera.setCenter(*center)
        if angles:
            self.camera.setAngles(angles)
#            self.camera.setRotation(*angles)
        self.camera.setDist(dist)
        self.camera.setLens(45.,self.aspect)
        self.camera.setClip(0.01*dist,100.*dist)


    def zoom(self,f):
        """Dolly zooming."""
        self.camera.setDist(f*self.camera.getDist())


    def draw_cursor(self,x,y):
        if self.cursor:
            self.removeDecoration(self.cursor)
        w,h = GD.cfg.get('pick/size',(20,20))
        self.cursor = decors.Grid(x-w/2,y-h/2,x+w/2,y+h/2,color='cyan',linewidth=1)
        self.addDecoration(self.cursor)

    def draw_rectangle(self,x,y):
        if self.cursor:
            self.removeDecoration(self.cursor)
        self.cursor = decors.Grid(self.statex,self.statey,x,y,color='cyan',linewidth=1)
        self.addDecoration(self.cursor)

    def save(self,*args):
        return image.save(self,*args)

### End
