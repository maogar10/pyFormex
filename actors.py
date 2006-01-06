# canvas.py
# $Id$
"""OpenGL actors for populating the 3D scene(3D)."""

import OpenGL.GL as GL
import OpenGL.GLU as GLU

from colors import *
from formex import *

### Some drawing functions ###############################################

def drawCube(s,color=[red,cyan,green,magenta,blue,yellow]):
    """Draws a centered cube with side 2*s and colored faces.

    Colors are specified in the order [FRONT,BACK,RIGHT,LEFT,TOP,BOTTOM].
    """
    vertices = [[s,s,s],[-s,s,s],[-s,-s,s],[s,-s,s],[s,s,-s],[-s,s,-s],[-s,-s,-s],[s,-s,-s]]
    planes = [[0,1,2,3],[4,5,6,7],[0,3,7,4],[1,2,6,5],[0,1,5,4],[3,2,6,7]]
    GL.glBegin(GL.GL_QUADS)
    for i in range(6):
        #glNormal3d(0,1,0);
        GL.glColor(*color[i])
        for j in planes[i]:
            GL.glVertex3f(*vertices[j])
    GL.glEnd()

def drawSphere(s,color=cyan,ndiv=8):
    """Draws a centered sphere with radius s in given color."""
    quad = GLU.gluNewQuadric()
    GLU.gluQuadricNormals(quad, GLU.GLU_SMOOTH)
    GL.glColor(*color)
    GLU.gluSphere(quad,s,ndiv,ndiv)


### Actors ###############################################
#
# Actors are anything that can be drawn in an openGL 3D scene.
# An actor minimally needs two functions:
#   bbox() : to calculate the bounding box of the actor.
#   draw(wireframe=False) : to actually draw the actor.

class CubeActor:
    """An OpenGL actor with cubic shape and 6 colored sides."""

    def __init__(self,size,color=[red,cyan,green,magenta,blue,yellow]):
        self.size = size
        self.color = color

    def bbox(self):
        return (0.5 * self.size) * array([[-1.,-1.,-1.],[1.,1.,1.]])

    def draw(self,wireframe=False):
        """Draw the cube."""
        drawCube(self.size,self.color)

class TriadeActor:
    """An OpenGL actor representing a triade of global axes."""

    def __init__(self,size,color=[red,green,blue,cyan,magenta,yellow]):
        self.size = size
        self.color = color

    def bbox(self):
        return (0.5 * self.size) * array([[0.,0.,0.],[1.,1.,1.]])

    def draw(self,wireframe=False):
        """Draw the triade."""
        GL.glShadeModel(GL.GL_FLAT)
        GL.glPolygonMode(GL.GL_FRONT, GL.GL_FILL)
        GL.glPolygonMode(GL.GL_BACK, GL.GL_LINE)
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glColor(*self.color[0])
        GL.glVertex3f(0.0,0.0,0.0)
        GL.glVertex3f(1.0,0.0,0.0)
        GL.glVertex3f(0.0,1.0,0.0)
        GL.glColor(*self.color[1])
        GL.glVertex3f(0.0,0.0,0.0)
        GL.glVertex3f(0.0,1.0,0.0)
        GL.glVertex3f(0.0,0.0,1.0)
        GL.glColor(*self.color[2])
        GL.glVertex3f(0.0,0.0,0.0)
        GL.glVertex3f(0.0,0.0,1.0)
        GL.glVertex3f(1.0,0.0,0.0)
##        GL.glColor(*self.color[3])
##        GL.glVertex3f(0.0,0.0,0.0)
##        GL.glVertex3f(0.0,1.0,0.0)
##        GL.glVertex3f(1.0,0.0,0.0)
##        GL.glColor(*self.color[4])
##        GL.glVertex3f(0.0,0.0,0.0)
##        GL.glVertex3f(0.0,0.0,1.0)
##        GL.glVertex3f(0.0,1.0,0.0)
##        GL.glColor(*self.color[5])
##        GL.glVertex3f(0.0,0.0,0.0)
##        GL.glVertex3f(1.0,0.0,0.0)
##        GL.glVertex3f(0.0,0.0,1.0)
        GL.glEnd()
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(*black)
        GL.glVertex3f(0.0,0.0,0.0)
        GL.glVertex3f(2.0,0.0,0.0)
        GL.glVertex3f(0.0,0.0,0.0)
        GL.glVertex3f(0.0,2.0,0.0)
        GL.glVertex3f(0.0,0.0,0.0)
        GL.glVertex3f(0.0,0.0,2.0)
        GL.glEnd()


class FormexActor(Formex):
    """An OpenGL actor which is a Formex."""

    def __init__(self,F,color=[black],linewidth=1.0):
        """Create a multicolored Formex actor.

        The colors argument specifies a list of OpenGL colors for each
        of the property values in the Formex. If the list has less
        values than the PropSet, it is wrapped around. It can also be
        a single OpenGL color, which will be used for all elements.
        The user can specify a linewidth to be used when drawing
        in wireframe mode
        """
        Formex.__init__(self,F.f,F.p)
        self.list = None
        if type(self.p) == type(None):
            self.setProp(arange(self.nelems()))
            print "Properties:",self.p
        if len(color) == 3 and type(color[0]) == float and \
           type(color[1]) == float and type(color[2]) == float:
            color = [ color ] # turn single color into a list
        # now color should be a list of colors, possibly to short
        mprop = max(self.propSet()) + 1
        self.color = [ color[v % len(color)] for v in range(mprop) ]
        self.linewidth = float(linewidth)
        if self.nnodel() == 1:
            self.setMark(self.size()/200,"cube")

    def draw(self,wireframe=True):
        """Draw the formex."""
        nnod = self.nnodel()
        nelem = self.nelems()
        if nnod == 2:
            GL.glLineWidth(self.linewidth)
            GL.glBegin(GL.GL_LINES)
            for i in range(nelem):
                col = self.color[int(self.p[i])]
                GL.glColor3f(*(col))
                for nod in self[i]:
                    GL.glVertex3f(*nod)
            GL.glEnd()
            
        # We need to further color setting only nnod=2 done 
        elif nnod == 1:
            for el in self.data():
                GL.glPushMatrix()
                GL.glTranslatef (*el[0])
                GL.glCallList(self.mark)
                GL.glPopMatrix()
                
        elif wireframe:
            GL.glLineWidth(self.linewidth)
            for i in range(nelem):
                col = self.color[self.p[i]]
                GL.glColor3f(*(col))
                GL.glBegin(GL.GL_LINE_LOOP)
                for nod in self[i]:
                    GL.glVertex3f(*nod)
                GL.glEnd()
                
        elif nnod == 3:
            GL.glBegin(GL.GL_TRIANGLES)
            for el in self.data():
                for nod in el:
                    GL.glVertex3f(*nod)
            GL.glEnd()
            
        elif nnod == 4:
            GL.glBegin(GL.GL_QUADS)
            for el in self.data():
                for nod in el:
                    GL.glVertex3f(*nod)
            GL.glEnd()
            
        else:
            for el in self.data():
                GL.glBegin(GL.GL_POLYGON)
                for nod in el:
                    GL.glVertex3f(*nod)
                GL.glEnd()

    def setMark(self,size,type):
        """Create a symbol for drawing vertices."""
        self.mark = GL.glGenLists(1)
        GL.glNewList(self.mark,GL.GL_COMPILE)
        if type == "sphere":
            drawSphere(size)
        else:
            drawCube(size)
        GL.glEndList()
