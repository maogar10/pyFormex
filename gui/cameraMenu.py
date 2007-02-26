#!/usr/bin/env python
# $Id$
##
## This file is part of pyFormex 0.4.2 Release Mon Feb 26 08:57:40 2007
## pyFormex is a python implementation of Formex algebra
## Homepage: http://pyformex.berlios.de/
## Distributed under the GNU General Public License, see file COPYING
## Copyright (C) Benedict Verhegghe except where stated otherwise 
##
"""Functions from the Camera menu."""

import globaldata as GD

         
def zoomIn():
    GD.canvas.zoom(1./float(GD.cfg['gui/zoomfactor']))
    GD.canvas.update()
def zoomOut():
    GD.canvas.zoom(float(GD.cfg['gui/zoomfactor']))
    GD.canvas.update()
##def panRight():
##    canvas.camera.pan(+5)
##    canvas.update()   
##def panLeft():
##    canvas.camera.pan(-5)
##    canvas.update()   
##def panUp():
##    canvas.camera.pan(+5,0)
##    canvas.update()   
##def panDown():
##    canvas.camera.pan(-5,0)
##    canvas.update()   
def rotRight():
    GD.canvas.camera.rotate(+float(GD.cfg['gui/rotfactor']),0,1,0)
    GD.canvas.update()   
def rotLeft():
    GD.canvas.camera.rotate(-float(GD.cfg['gui/rotfactor']),0,1,0)
    GD.canvas.update()   
def rotUp():
    GD.canvas.camera.rotate(-float(GD.cfg['gui/rotfactor']),1,0,0)
    GD.canvas.update()   
def rotDown():
    GD.canvas.camera.rotate(+float(GD.cfg['gui/rotfactor']),1,0,0)
    GD.canvas.update()   
def twistLeft():
    GD.canvas.camera.rotate(+float(GD.cfg['gui/rotfactor']),0,0,1)
    GD.canvas.update()   
def twistRight():
    GD.canvas.camera.rotate(-float(GD.cfg['gui/rotfactor']),0,0,1)
    GD.canvas.update()   
def transLeft():
    val = float(GD.cfg['gui/panfactor']) * GD.canvas.camera.getDist()
    GD.canvas.camera.translate(-val,0,0,GD.cfg['draw/localaxes'])
    GD.canvas.update()   
def transRight():
    val = float(GD.cfg['gui/panfactor']) * GD.canvas.camera.getDist()
    GD.canvas.camera.translate(+val,0,0,GD.cfg['draw/localaxes'])
    GD.canvas.update()   
def transDown():
    val = float(GD.cfg['gui/panfactor']) * GD.canvas.camera.getDist()
    GD.canvas.camera.translate(0,-val,0,GD.cfg['draw/localaxes'])
    GD.canvas.update()   
def transUp():
    val = float(GD.cfg['gui/panfactor']) * GD.canvas.camera.getDist()
    GD.canvas.camera.translate(0,+val,0,GD.cfg['draw/localaxes'])
    GD.canvas.update()   
def dollyIn():
    GD.canvas.camera.dolly(1./float(GD.cfg['gui/zoomfactor']))
    GD.canvas.update()   
def dollyOut():
    GD.canvas.camera.dolly(float(GD.cfg['gui/zoomfactor']))
    GD.canvas.update()   
def setPerspective(mode=True):
    GD.canvas.camera.setPerspective(mode)
    GD.canvas.display()
    GD.canvas.update()
def setProjection():
    setPerspective(False)
