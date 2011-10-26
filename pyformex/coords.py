# $Id$
##
##  This file is part of pyFormex 0.8.4 Release Sat Jul  9 14:43:11 2011
##  pyFormex is a tool for generating, manipulating and transforming 3D
##  geometrical models by sequences of mathematical operations.
##  Homepage: http://pyformex.org   (http://pyformex.berlios.de)
##  Copyright (C) Benedict Verhegghe (benedict.verhegghe@ugent.be) 
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
"""A structured collection of 3D coordinates.

The :mod:`coords` module defines the :class:`Coords` class, which is the basic
data structure in pyFormex to store the coordinates of points in a 3D space.

This module implements a data class for storing large sets of 3D coordinates
and provides an extensive set of methods for transforming these coordinates.
Most of pyFormex's classes which represent geometry (e.g. :class:`Geometry`,
:class:`Formex`, :class:`Mesh`, :class:`TriSurface`, :class:`Curve`) use a
:class:`Coords` object to store their coordinates, and thus inherit all the
transformation methods of this class.

While the user will mostly use the higher level classes, he might occasionally
find good reason to use the :class:`Coords` class directly as well.
"""

from arraytools import *
from lib import misc
from pyformex import options
from utils import deprecated,deprecation
from plugins import inertia


def bbox(objects):
    """Compute the bounding box of a list of objects.

    The bounding box of an object is the smallest rectangular cuboid
    in the global Cartesian coordinates, such that no points of the
    objects lie outside that cuboid.
    
    Parameters:

    - `objects`: a list of objects which all should have the method
      :meth:`bbox`. The resulting bounding encloses all the objects
      in the list. Objects whose :meth:`bbox` method returns `None`
      are ignored.

    Returns:
      A Coords object with two points: the first contains the minimal
      coordinate values, the second has the maximal ones. 

    Example:
    
      >>> from formex import *
      >>> bbox([Coords([-1.,1.,0.]),Formex('l:5')])
      Coords([[-1.,  0.,  0.],
             [ 1.,  1.,  0.]], dtype=float32)
      
    """
    bboxes = [f.bbox() for f in objects if hasattr(f,'bbox') and not isnan(f.bbox()).any()]
    bboxes = [bb for bb in bboxes if bb is not None]
    if len(bboxes) == 0:
        o = origin()
        bboxes = [ [o,o] ]
    return Coords(concatenate(bboxes)).bbox()


###########################################################################
##
##   class Coords
##
#########################
#
class Coords(ndarray):
    """A structured collection of points in a 3D cartesian space.
    
    The :class:`Coords` class is the basic data structure used throughout
    pyFormex to store coordinates of points in a 3D space.
    It is used by other classes, such as :class:`Formex`
    and :class:`Surface`, which thus inherit the same transformation
    capabilities. Applications will mostly use the higher level
    classes, which usually have more elaborated consistency checking
    and error handling.
    
    :class:`Coords` is implemented as a subclass of :class:`numpy.ndarray`,
    and thus inherits all its methods.
    The last axis of the :class:`Coords` always has a length equal to 3.
    Each set of 3 values along the last axis represents a single point
    in 3D cartesian space. The float datatype is only checked at creation
    time. It is the responsibility of the user to keep this consistent
    throughout the lifetime of the object.

    A new Coords object is created with the following syntax ::
    
      Coords(data=None,dtyp=Float,copy=False)

    Parameters:

    - `data`: array_like of type float.
      The last axis should have a length of 1, 2 or 3, bu will always be
      expanded to 3.
      If no data are specified, an empty Coords with shape (0,3) is created.

    - `dtyp`: the float datatype to be used.
      It not specified, the datatype of `data` is used, or the default
      :data:`Float` (which is equivalent to :data:`numpy.float32`). 

    - `copy`: boolean.
      If ``True``, the data are copied. The default setting will try to use
      the original data if possible, e.g. if `data` is a correctly shaped and
      typed :class:`numpy.ndarray`.

    Example:
    
      >>> Coords([1.,0.])
      Coords([ 1.,  0.,  0.], dtype=float32)
      
    """
    #
    # :DEV
    # Because we have a __new__ constructor here and no __init__,
    # we have to list the arguments explicitely in the docstring above.
    #
    def __new__(clas, data=None, dtyp=Float, copy=False):
        """Create a new instance of :class:`Coords`."""
        if data is None:
            # create an empty array : we need at least a 2D array
            # because we want the last axis to have length 3 and
            # we also need an axis with length 0 to have size 0
            ar = ndarray((0,3),dtype=dtyp)
        else:
            # turn the data into an array, and copy if requested
            # DO NOT ADD ndmin=1 HERE ! (see below)
            ar = array(data,dtype=dtyp,copy=copy)

        #
        # The Coords object needs to be at least 1-D array, no a scalar
        # We could force 'ar' above to be at least 1-D, but that would 
        # turn every scalar into a 1-D vector, which would circumvent
        # detection of input errors (e.g. with translation, where input
        # can be either a vector or an axis number)
        #
        if ar.ndim == 0:
            raise ValueError,"Expected array data, not a scalar"
        
        if ar.shape[-1] == 3:
            pass
        elif ar.shape[-1] in [1,2]:
            # make last axis length 3, adding 0 values
            ar = growAxis(ar,3-ar.shape[-1],-1)
        elif ar.shape[-1] == 0:
            # allow empty coords objects 
            ar = ar.reshape(0,3)
        else:
            raise ValueError,"Expected a length 1,2 or 3 for last array axis"

        # Make sure dtype is a float type
        if ar.dtype.kind != 'f':
            ar = ar.astype(Float)
 
        # Transform 'subarr' from an ndarray to our new subclass.
        ar = ar.view(clas)

        return ar

        
###########################################################################
    #
    #   Methods that return information about a Coords object or other
    #   views on the object data, without changing the object itself.

    # General

    def points(self):
        """Returns the :class:`Coords` object as a simple set of points.

        This reshapes the array to a 2-dimensional array, flattening
        the structure of the points.
        """
        return self.reshape((-1,3))
    
    def pshape(self):
        """Returns the shape of the :class:`Coords` object.

        This is the shape of the `NumPy`_ array with the last axis removed.
        The full shape of the :class:`Coords` array can be obtained from
        its shape attribute.
        """
        return self.shape[:-1]

    def npoints(self):
        """Return the total number of points."""
        return asarray(self.shape[:-1]).prod()

    ncoords = npoints

    def x(self):
        """Return the X-coordinates of all points.

        Returns an array with all the X-coordinates in the Coords.
        The returned array has the same shape as the Coords array along
        its first ndim-1 axes.
        This is equivalent with ::
        
          self[...,0]
        """
        return self[...,0]
    def y(self):
        """Return the Y-coordinates of all points.

        Returns an array with all the Y-coordinates in the Coords.
        The returned array has the same shape as the Coords array along
        its first ndim-1 axes.
        This is equivalent with ::
        
          self[...,1]
        """
        return self[...,1]
    def z(self):
        """Return the Z-coordinates of all points.

        Returns an array with all the Z-coordinates in the Coords.
        The returned array has the same shape as the Coords array along
        its first ndim-1 axes.
        This is equivalent with ::
        
          self[...,0]
        """
        return self[...,2]


    # Size
    
    def bbox(self):
        """Return the bounding box of a set of points.

        The bounding box is the smallest rectangular volume in the global
        coordinates, such that no point of the :class:`Coords` are outside
        that volume.

        Returns:
        
          A Coords object with shape(2,3): the first point contains the
          minimal coordinates, the second has the maximal ones. 

        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).bbox()
          [[ 0.  0.  0.]
           [ 3.  3.  0.]]
        """
        if self.size > 0:
            s = self.points()
            bbox = row_stack([ s.min(axis=0), s.max(axis=0) ])
        else:
            o = origin()
            bbox = [o,o]
        return Coords(bbox)


    def center(self):
        """Return the center of the :class:`Coords`.

        The center of a :class:`Coords` is the center of its bbox().
        The return value is a (3,) shaped :class:`Coords` object.
        
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).center()
          [ 1.5  1.5  0. ]

        See also: :meth:`centroid`
        """
        X0,X1 = self.bbox()
        return 0.5 * (X0+X1)


    def average(self,wts=None,axis=0):
        """Return a (weighted) average of the :class:`Coords`.

        The average of a :class:`Coords` is a :class:`Coords` with one
        axis less than the original, obtained by averaging all the points
        along that axis.
        The weights array can either be 1-D (in which case its length must
        be the size along the given axis) or of the same shape as a.
        Weights can be specified as a 1-D array with the length of that axis,
        or as an array with the same shape as the :class:`Coords`.
        The sum of the weights (along the specified axis if not 1-D) will
        generally be equal to 1.0.
        If wts=None, then all points are assumed to have a weight equal to
        one divided by the length of the specified axis.

        Example:

          >>> print Coords([[[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]],\
                  [[4.,0.,0.],[5.,0.,0.],[6.,0.,0.]]]).average()
          [[ 2.  0.  0.]
           [ 3.  0.  0.]
           [ 4.  0.  0.]]
          >>> print Coords([[[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]],\
                  [[4.,0.,0.],[5.,0.,0.],[6.,0.,0.]]]).average(axis=1)
          [[ 1.  0.  0.]
           [ 5.  0.  0.]]
          >>> print Coords([[[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]],\
                  [[4.,0.,0.],[5.,0.,0.],[6.,0.,0.]]]).average(wts=[0.5,0.25,0.25],axis=1)
          [[ 0.75  0.    0.  ]
           [ 4.75  0.    0.  ]]
        """
        return average(self,weights=wts,axis=axis)
        

    def centroid(self):
        """Return the centroid of the :class:`Coords`.

        The centroid of a :class:`Coords` is the point whose coordinates
        are the mean values of all points.
        The return value is a (3,) shaped :class:`Coords` object.
        
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).centroid()
          [ 1.  1.  0.]
          
        See also: :meth:`center`
        """
        return self.points().mean(axis=0)


    def centroids(self):
        return self


    def sizes(self):
        """Return the sizes of the :class:`Coords`.

        Return an array with the length of the bbox along the 3 axes.
        
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).sizes()
          [ 3.  3.  0.]
          
        """
        X0,X1 = self.bbox()
        return X1-X0


    def dsize(self):
        """Return an estimate of the global size of the :class:`Coords`.

        This estimate is the length of the diagonal of the bbox().
        
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).dsize()
          4.24264
          
        """
        X0,X1 = self.bbox()
        return length(X1-X0)

    
    def bsphere(self):
        """Return the diameter of the bounding sphere of the :class:`Coords`.

        The bounding sphere is the smallest sphere with center in the
        center() of the :class:`Coords`, and such that no points of the
        :class:`Coords` are lying outside the sphere.
        
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).bsphere()
          2.12132
          
        """
        return self.distanceFromPoint(self.center()).max()


    # Inertia

    def inertia(self,mass=None):
        """Return inertia related quantities of the :class:`Coords`.
        
        This returns the center of gravity, the principal axes of inertia,
        the principal moments of inertia and the inertia tensor.
        """
        if mass is not None:
            mass = mass.reshape(self.npoints(),1)
        ctr,I = inertia.inertia(self.points(),mass)
        Iprin,Iaxes = inertia.principal(I,sort=True,right_handed=True)
        return (ctr,Iaxes,Iprin,I)


    #  Distance

    def distanceFromPlane(self,p,n):
        """Return the distance of all points from the plane (p,n).

        p is a point specified by 3 coordinates.
        n is the normal vector to a plane, specified by 3 components.

        The return value is a float array with shape ``self.pshape()`` with
        the distance of each point to the plane through p and having normal n.
        Distance values are positive if the point is on the side of the
        plane indicated by the positive normal.
        
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).distanceFromPlane([0.,0.,0.],[1.,0.,0.])
          [[ 0.  3.  0.]]
          
        """
        p = asarray(p).reshape((3))
        n = asarray(n).reshape((3))
        n = normalize(n)
        d = inner(self,n) - inner(p,n)
        return d


    def distanceFromLine(self,p,n):
        """Return the distance of all points from the line (p,n).

        p,n are (1,3) or (npts,3) arrays defining 1 or npts lines
        p is a point on the line specified by 3 coordinates.
        n is a vector specifying the direction of the line through p.

        The return value is a [...] shaped array with the distance of
        each point to the line through p with direction n.
        All distance values are positive or zero.

        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).distanceFromLine([0.,0.,0.],[1.,0.,0.])
          [[ 0.  0.  3.]]
          
        """
        p = asarray(p)#.reshape((3))
        n = asarray(n)#.reshape((3))
        t = cross(n,p-self)
        d = sqrt(sum(t*t,-1)) / length(n)
        return d


    def distanceFromPoint(self,p):
        """Return the distance of all points from the point p.

        p is a single point specified by 3 coordinates.

        The return value is a [...] shaped array with the distance of
        each point to point p.
        All distance values are positive or zero.
        Example:

          >>> print Coords([[[0.,0.,0.],[3.,0.,0.],[0.,3.,0.]]]).distanceFromPoint([0.,0.,0.])
          [[ 0.  3.  3.]]
          
        """
        p = asarray(p).reshape((3))
        d = self-p
        return sqrt(sum(d*d,-1))


    def closestToPoint(self,p):
        """Return the point closest to point p.

        """
        d = self.distanceFromPoint(p)
        return self.points()[d.argmin()]
    

    def directionalSize(self,n,p=None,_points=False):
        """Return the extreme distances from the plane p,n.

        The direction n can be specified by a 3 component vector or by
        a single integer 0..2 designing one of the coordinate axes.

        p is any point in space. If not specified, it is taken as the
        center() of the Coords.

        The return value is a tuple of two float values specifying the
        extreme distances from the plane p,n.
        """
        n = unitVector(n)

        if p is None:
            p = self.center()
        else:
            p = Coords(p)
        
        d = self.distanceFromPlane(p,n)
        dmin,dmax = d.min(),d.max()

        if _points:
            return [p+dmin*n, p+dmax*n]
        else:
            return dmin,dmax


    def directionalExtremes(self,n,p=None):
        """Return extremal planes in the direction n.

        `n` and `p` have the same meaning as in `directionalSize`.

        The return value is a list of two points on the line (p,n),
        such that the planes with normal n through these points define
        the extremal planes of the Coords.
        """
        return self.directionalSize(n,p,_points=True)


    def directionalWidth(self,n):
        """Return the width of a Coords in the given direction.

        The direction can be specified by a 3 component vector or by
        a single integer 0..2 designating one of the coordinate axes.

        The return value is the thickness of the object in the direction n.
        """
        dmin,dmax = self.directionalSize(n)
        return dmax-dmin


    # Test position

    def test(self,dir=0,min=None,max=None,atol=0.):
        """Flag points having coordinates between min and max.

        This function is very convenient in clipping a :class:`Coords` in a
        specified
        direction. It returns a 1D integer array flagging (with a value 1 or
        True) the elements having nodal coordinates in the required range.
        Use where(result) to get a list of element numbers passing the test.
        Or directly use clip() or cclip() to create the clipped :class:`Coords`.
        
        The test plane can be define in two ways depending on the value of dir.
        If dir == 0, 1 or 2, it specifies a global axis and min and max are
        the minimum and maximum values for the coordinates along that axis.
        Default is the 0 (or x) direction.

        Else, dir should be compatible with a (3,) shaped array and specifies
        the direction of the normal on the planes. In this case, min and max
        are points and should also evaluate to (3,) shaped arrays.

        One of the two clipping planes may be left unspecified.
        """
        if min is None and max is None:
            raise ValueError,"At least one of min or max have to be specified."

        if type(dir) == int:
            if not min is None:
                T1 = self[...,dir] > min - atol
            if not max is None:
                T2 = self[...,dir] < max + atol
        else:
            if not min is None:
                T1 = self.distanceFromPlane(min,dir) > - atol
            if not max is None:
                T2 = self.distanceFromPlane(max,dir) < atol

        if min is None:
            T = T2
        elif max is None:
            T = T1
        else:
            T = T1 * T2
        return T


    ## THIS IS A CANDIDATE FOR THE LIBRARY
    ## (possibly in a more general arrayprint form)
    ## (could be common with calpy)
    
    def fprint(self,fmt="%10.3e %10.3e %10.3e"):
        """Formatted printing of a :class:`Coords` object.

        The supplied format should contain 3 formatting sequences for the
        three coordinates of a point.
        """
        for p in self.points():
            print(fmt % tuple(p))



##############################################################################

    def set(self,f):
        """Set the coordinates from those in the given array."""
        self[...] = f      # do not be tempted to use self = f !

##############################################################################
    #
    #   Transformations that preserve the topology (but change coordinates)
    #
    #   A. Affine transformations
    #
    #      Scaling
    #      Translation
    #      Central Dilatation = Scaling + Translation
    #      Rotation
    #      Shear
    #      Reflection
    #      Affine
    #
    #  The following methods return transformed coordinates, but by default
    #  they do not change the original data. If the optional argument inplace
    #  is set True, however, the coordinates are changed inplace. 

   
    def scale(self,scale,dir=None,inplace=False):
        """Return a copy scaled with scale[i] in direction i.

        The scale should be a list of 3 scaling factors for the 3 axis
        directions, or a single scaling factor.
        In the latter case, dir (a single axis number or a list) may be given
        to specify the direction(s) to scale. The default is to produce a
        homothetic scaling.

        Example:

          >>> print Coords([1.,1.,1.]).scale(2)
          [ 2.  2.  2.]
          >>> print Coords([1.,1.,1.]).scale([2,3,4])
          [ 2.  3.  4.]
          
        """
        if inplace:
            out = self
        else:
            out = self.copy()
        if dir is None:
            out *= scale
        else:
            out[...,dir] *= scale
        return out
    

    def translate(self,dir,step=None,inplace=False):
        """Translate a :class:`Coords` object.

        Translates the Coords in the direction `dir` over a distance
        `step * length(dir)`.

        Parameters:

        - `dir`: specifies the direction and distance of the translation. It
          can be either 

          - an axis number (0,1,2), specifying a unit vector in the direction
            of one of the coordinate axes.
          - a single translation vector,
          - an array of translation vectors, compatible with the Coords shape.
        
        - `step`: If specified, the translation vector specified by `dir` will
          be multiplied with this value. It is commonly used with unit `dir`
          vectors to set the translation distance.
          
        Example:

          >>> x = Coords([1.,1.,1.])
          >>> print x.translate(1)
          [ 1.  2.  1.]
          >>> print x.translate(1,1.)
          [ 1.  2.  1.]
          >>> print x.translate([0,1,0])
          [ 1.  2.  1.]
          >>> print x.translate([0,2,0],0.5)
          [ 1.  2.  1.]
          
        """
        if inplace:
            out = self
        else:
            out = self.copy()
        if type(dir) is int:
            dir = unitVector(dir)
        dir = Coords(dir,copy=True)
        if step is not None:
            dir *= step
        out += dir
        return out


    def centered(self):
        """Return a centered copy of the Coords.

        Returns a Coords which is a translation thus that the center
        coincides with the origin.
        This is equivalent with::

          self.trl(-self.center())

        """
        return self.trl(-self.center())


    def align(self,alignment='---'):
        """Align the Coords along the global axes.

        Alignment involves a translation such that the bounding box
        of the Coords object becomes aligned on the origin of the global axes.
        The requested alignment is determined by a string of three characters,
        one for each of the coordinate axes. The character determines how
        the structure is aligned in the corresponding direction:

        - '-': aligned on the minimal value of the bounding box,
        - '+': aligned on the maximal value of the bounding box,
        - '0': aligned on the middle value of the bounding box.
        
        Any other value will make the alignment in that direction unchanged.

        The default alignment string '---' results in a translation which puts
        all the points in the octant with all positive coordinate values.
        A string '000' will center the object around the origin, just like
        the (slightly faster) :meth:`centered` method, which is .
        """
        trl = zeros(3)
        bb = self.bbox()
        al = { '-': bb[0], '+': bb[1], '0': 0.5*(bb[0]+bb[1]) }
        for i,c in enumerate(alignment):
            if c in al:
                trl[i] = -al[c][i]
        return self.translate(trl)
    

    def rotate(self,angle,axis=2,around=None):
        """Return a copy rotated over angle around axis.

        The angle is specified in degrees.
        The axis is either one of (0,1,2) designating the global axes,
        or a vector specifying an axis through the origin.
        If no axis is specified, rotation is around the 2(z)-axis. This is
        convenient for working on 2D-structures.

        As a convenience, the user may also specify a 3x3 rotation matrix,
        in which case the function rotate(mat) is equivalent to affine(mat).

        All rotations are performed around the point [0,0,0], unless a
        rotation origin is specified in the argument 'around'. 
        """
        mat = asarray(angle)
        if mat.size == 1:
            mat = rotationMatrix(angle,axis)
        if mat.shape != (3,3):
            raise ValueError,"Rotation matrix should be 3x3"
        if around is not None:
            around = asarray(around)
            out = self.translate(-around)
        else:
            out = self
        return out.affine(mat,around)
    

    def shear(self,dir,dir1,skew,inplace=False):
        """Return a copy skewed in the direction dir of plane (dir,dir1).

        The coordinate dir is replaced with (dir + skew * dir1).
        """
        if inplace:
            out = self
        else:
            out = self.copy()
        out[...,dir] += skew * out[...,dir1]
        return out


    # THIS SHOULD BE GENERALIZED TO TAKE SAME `dir` OPTIONS AS translate
    def reflect(self,dir=0,pos=0.,inplace=False):
        """Reflect the coordinates in direction dir against plane at pos.

        Parameters:

        - `dir`: int: direction of the reflection (default 0)
        - `pos`: float: offset of the mirror plane from origin (default 0.0)
        - `inplace`: boolean: change the coordinates inplace (default False)
        """
        if inplace:
            out = self
        else:
            out = self.copy()
        out[...,dir] = 2*pos - out[...,dir]
        return out
    

    def affine(self,mat,vec=None):
        """Returns a general affine transform of the :class:`Coords` object.

        `mat`: a 3x3 float matrix
        
        `vec`: a length 3 list or array of floats
        
        The returned object has coordinates given by ``self * mat + vec``.
        """
        out = dot(self,mat)
        if vec is not None:
            out += vec
        return out
#
#
#   B. Non-Affine transformations.
#
#      These always return copies !
#
#        Cylindrical, Spherical, Isoparametric
#

    def cylindrical(self,dir=[0,1,2],scale=[1.,1.,1.],angle_spec=Deg):
        """Converts from cylindrical to cartesian after scaling.

        dir specifies which coordinates are interpreted as resp.
        distance(r), angle(theta) and height(z). Default order is [r,theta,z].
        scale will scale the coordinate values prior to the transformation.
        (scale is given in order r,theta,z).
        The resulting angle is interpreted in degrees.
        """
        # We put in a optional scaling, because doing this together with the
        # transforming is cheaper than first scaling and then transforming.
        f = zeros_like(self)
        theta = (scale[1]*angle_spec) * self[...,dir[1]]
        r = scale[0] * self[...,dir[0]]
        f[...,0] = r*cos(theta)
        f[...,1] = r*sin(theta)
        f[...,2] = scale[2] * self[...,dir[2]]
        return f


    def hyperCylindrical(self,dir=[0,1,2],scale=[1.,1.,1.],rfunc=None,zfunc=None,angle_spec=Deg):
        if rfunc is None:
            rfunc = lambda x:1
        if zfunc is None:
            zfunc = lambda x:1
        f = zeros_like(self)
        theta = (scale[1]*angle_spec) * self[...,dir[1]]
        r = scale[0] * rfunc(theta) * self[...,dir[0]]
        f[...,0] = r * cos(theta)
        f[...,1] = r * sin(theta)
        f[...,2] = scale[2] * zfunc(theta) * self[...,dir[2]]
        return f
    

    def toCylindrical(self,dir=[0,1,2],angle_spec=Deg):
        """Converts from cartesian to cylindrical coordinates.

        dir specifies which coordinates axes are parallel to respectively the
        cylindrical axes distance(r), angle(theta) and height(z). Default
        order is [x,y,z].
        The angle value is given in degrees.
        """
        f = zeros_like(self)
        x,y,z = [ self[...,i] for i in dir ]
        f[...,0] = sqrt(x*x+y*y)
        f[...,1] = arctand2(y,x,angle_spec)
        f[...,2] = z
        return f

    
    def spherical(self,dir=[0,1,2],scale=[1.,1.,1.],angle_spec=Deg,colat=False):
        """Converts from spherical to cartesian after scaling.

        - `dir` specifies which coordinates are interpreted as resp.
          longitude(theta), latitude(phi) and distance(r).
        - `scale` will scale the coordinate values prior to the transformation.

        Angles are interpreted in degrees.
        Latitude, i.e. the elevation angle, is measured from equator in
        direction of north pole(90). South pole is -90.

        If colat=True, the third coordinate is the colatitude (90-lat) instead.
        """
        f = self.reshape((-1,3))
        theta = (scale[0]*angle_spec) * f[:,dir[0]]
        phi = (scale[1]*angle_spec) * f[:,dir[1]]
        r = scale[2] * f[:,dir[2]]
        if colat:
            phi = 90.0*angle_spec - phi
        rc = r*cos(phi)
        f = column_stack([rc*cos(theta),rc*sin(theta),r*sin(phi)])
        return f.reshape(self.shape)


    def superSpherical(self,n=1.0,e=1.0,k=0.0, dir=[0,1,2],scale=[1.,1.,1.],angle_spec=Deg,colat=False):
        """Performs a superspherical transformation.

        superSpherical is much like spherical, but adds some extra
        parameters to enable the creation of virtually any surface.

        Just like with spherical(), the input coordinates are interpreted as
        the longitude, latitude and distance in a spherical coordinate system.

        `dir` specifies which coordinates are interpreted as resp.
        longitude(theta), latitude(phi) and distance(r).
        Angles are then interpreted in degrees.
        Latitude, i.e. the elevation angle, is measured from equator in
        direction of north pole(90). South pole is -90.
        If colat=True, the third coordinate is the colatitude (90-lat) instead.

        `scale` will scale the coordinate values prior to the transformation.

        The `n` and `e` parameters define exponential transformations of the
        north_south (latitude), resp. the east_west (longitude) coordinates.
        Default values of 1 result in a circle.

        `k` adds 'eggness' to the shape: a difference between the northern and
        southern hemisphere. Values > 0 enlarge the southern hemishpere and
        shrink the northern.
        """
        def c(o,m):
            c = cos(o)
            return sign(c)*abs(c)**m
        def s(o,m):
            c = sin(o)
            return sign(c)*abs(c)**m

        f = self.reshape((-1,3))
        theta = (scale[0]*angle_spec) * f[:,dir[0]]
        phi = (scale[1]*angle_spec) * f[:,dir[1]]
        r = scale[2] * f[:,dir[2]]
        if colat:
            phi = 90.0*angle_spec - phi
        rc = r*c(phi,n)
        if k != 0:   # k should be > -1.0 !!!!
            x = sin(phi)
            rc *= (1-k*x)/(1+k*x)
        f = column_stack([rc*c(theta,e),rc*s(theta,e),r*s(phi,n)])
        return f.reshape(self.shape)


    def toSpherical(self,dir=[0,1,2],angle_spec=Deg):
        """Converts from cartesian to spherical coordinates.

        `dir` specifies which coordinates axes are parallel to respectively
        the spherical axes distance(r), longitude(theta) and latitude(phi).
        Latitude is the elevation angle measured from equator in direction
        of north pole(90). South pole is -90.
        Default order is [0,1,2], thus the equator plane is the (x,y)-plane.

        The returned angle values are given in degrees.
        """
        v = self[...,dir].reshape((-1,3))
        dist = sqrt(sum(v*v,-1))
        long = arctand2(v[:,0],v[:,2],angle_spec)
        lat = where(dist <= 0.0,0.0,arcsind(v[:,1]/dist,angle_spec))
        f = column_stack([long,lat,dist])
        return f.reshape(self.shape)


    def bump1(self,dir,a,func,dist):
        """Return a :class:`Coords` with a one-dimensional bump.

        - `dir` specifies the axis of the modified coordinates;
        - `a` is the point that forces the bumping;
        - `dist` specifies the direction in which the distance is measured;
        - `func` is a function that calculates the bump intensity from distance
          and should be such that ``func(0) != 0``.
        """
        f = self.copy()
        d = f[...,dist] - a[dist]
        f[...,dir] += func(d)*a[dir]/func(0)
        return f

    
    def bump2(self,dir,a,func):
        """Return a :class:`Coords` with a two-dimensional bump.

        dir specifies the axis of the modified coordinates;
        a is the point that forces the bumping;
        func is a function that calculates the bump intensity from distance
        !! func(0) should be different from 0.
        """
        f = self.copy()
        dist = [0,1,2]
        dist.remove(dir)
        d1 = f[...,dist[0]] - a[dist[0]]
        d2 = f[...,dist[1]] - a[dist[1]]
        d = sqrt(d1*d1+d2*d2)
        f[...,dir] += func(d)*a[dir]/func(0)
        return f

    
    # This is a generalization of both the bump1 and bump2 methods.
    # If it proves to be useful, it might replace them one day

    # An interesting modification might be to have a point for definiing
    # the distance and a point for defining the intensity (3-D) of the
    # modification
    def bump(self,dir,a,func,dist=None):
        """Return a :class:`Coords` with a bump.

        A bump is a modification of a set of coordinates by a non-matching
        point. It can produce various effects, but one of the most common
        uses is to force a surface to be indented by some point.
        
        dir specifies the axis of the modified coordinates;
        a is the point that forces the bumping;
        func is a function that calculates the bump intensity from distance
        (!! func(0) should be different from 0)
        dist is the direction in which the distance is measured : this can
        be one of the axes, or a list of one or more axes.
        If only 1 axis is specified, the effect is like function bump1
        If 2 axes are specified, the effect is like bump2
        This function can take 3 axes however.
        Default value is the set of 3 axes minus the direction of modification.
        This function is then equivalent to bump2.
        """
        f = self.copy()
        if dist == None:
            dist = [0,1,2]
            dist.remove(dir)
        try:
            l = len(dist)
        except TypeError:
            l = 1
            dist = [dist]
        d = f[...,dist[0]] - a[dist[0]]
        if l==1:
            d = abs(d)
        else:
            d = d*d
            for i in dist[1:]:
                d1 = f[...,i] - a[i]
                d += d1*d1
            d = sqrt(d)
        f[...,dir] += func(d)*a[dir]/func(0)
        return f


    def flare (self,xf,f,dir=[0,2],end=0,exp=1.):
        """Create a flare at the end of a :class:`Coords` block.

        The flare extends over a distance ``xf`` at the start (``end=0``)
        or end (``end=1``) in direction ``dir[0]`` of the coords block,
        and has a maximum amplitude of ``f`` in the ``dir[1]`` direction.
        """
        ix,iz = dir
        bb = self.bbox()
        if end == 0:
            xmin = bb[0][ix]
            endx = self.test(dir=ix,max=xmin+xf)
            func = lambda x: (1.-(x-xmin)/xf) ** exp
        else:
            xmax = bb[1][ix]
            endx = self.test(dir=ix,min=xmax-xf)
            func = lambda x: (1.-(xmax-x)/xf) ** exp
        x = self.copy()
        x[endx,iz] += f * func(x[endx,ix])
        return x


    def map(self,func):
        """Return a :class:`Coords` mapped by a 3-D function.

        This is one of the versatile mapping functions.
        func is a numerical function which takes three arguments and produces
        a list of three output values. The coordinates [x,y,z] will be
        replaced by func(x,y,z).
        The function must be applicable to arrays, so it should
        only include numerical operations and functions understood by the
        numpy module.
        This method is one of several mapping methods. See also map1 and mapd.

        Example:

          >>> print Coords([[1.,1.,1.]]).map(lambda x,y,z: [2*x,3*y,4*z])
          [[ 2.  3.  4.]]

        """
        # flatten coordinate sets to ease use of complicated functions
        # we should probably do this for map1 and mapd too
        X = self.points()
        f = zeros_like(X)
        f[...,0],f[...,1],f[...,2] = func(X.x(),X.y(),X.z())
        return f.reshape(self.shape)


    def map1(self,dir,func,x=None):
        """Return a :class:`Coords` where coordinate i is mapped by a 1-D function.

        `func` is a numerical function which takes one argument and produces
        one result. The coordinate dir will be replaced by func(coord[x]).
        If no x is specified, x is taken equal to dir. 
        The function must be applicable on arrays, so it should only
        include numerical operations and functions understood by the
        numpy module.
        This method is one of several mapping methods. See also map and mapd.
        """
        if x is None:
            x = dir
        f = self.copy()
        f[...,dir] = func(self[...,x])
        return f


    def mapd(self,dir,func,point,dist=None):
        """Maps one coordinate by a function of the distance to a point.

        `func` a numerical function which takes one argument and produces
        one result. The coordinate `dir` will be replaced by ``func(d)``,
        where ``d`` is calculated as the distance to `point`.
        The function must be applicable on arrays, so it should only
        include numerical operations and functions understood by the
        :mod:`numpy` module.
        By default, the distance d is calculated in 3-D, but one can specify
        a limited set of axes to calculate a 2-D or 1-D distance.
        This method is one of several mapping methods. See also
        :meth:`map3` and :meth:`map1`.
        
        Example:
        
          E.mapd(2,lambda d:sqrt(10**2-d**2),f.center(),[0,1])

        maps ``E`` on a sphere with radius 10.
        """
        f = self.copy()
        if dist == None:
            dist = [0,1,2]
        try:
            l = len(dist)
        except TypeError:
            l = 1
            dist = [dist]
        d = f[...,dist[0]] - point[dist[0]]
        if l==1:
            d = abs(d)
        else:
            d = d*d
            for i in dist[1:]:
                d1 = f[...,i] - point[i]
                d += d1*d1
            d = sqrt(d)
        f[...,dir] = func(d)
        return f


    def egg(self,k):
        """Maps the coordinates to an egg-shape"""
        return (1-k*self)/(1+k*self)


    def replace(self,i,j,other=None):
        """Replace the coordinates along the axes i by those along j.

        i and j are lists of axis numbers or single axis numbers.
        replace ([0,1,2],[1,2,0]) will roll the axes by 1.
        replace ([0,1],[1,0]) will swap axes 0 and 1.
        An optionally third argument may specify another :class:`Coords` object to take
        the coordinates from. It should have the same dimensions.
        """
        if other is None:
            other = self
        f = self.copy()
        f[...,i] = other[...,j]
        return f


    def swapAxes(self,i,j):
        """Swap coordinate axes i and j.

        Beware! This is different from numpy's swapaxes() method !
        """
        return self.replace([i,j],[j,i])


    def rollAxes(self,n=1):
        """Roll the axes over the given amount.

        Default is 1, thus axis 0 becomes the new 1 axis, 1 becomes 2 and
        2 becomes 0.
        """
        return roll(self, int(n) % 3,axis=-1)


    def projectOnPlane(self,n=2,P=[0.,0.,0.]):
        """Project a :class:`Coords` on a plane (or planes).

        Parameters:

        - `n`: the normal direction to the plane. It can be specified either
          by a list of three floats, or by a single integer (0, 1 or 2) to
          use one of the global axes.
        - `P`: a point on the plane, by default the global origin.
          If an int, the plane is the coordinate plane perpendicular to the

        ..note: For planes parallel to a coordinate plane, it is far more
          efficient to specify the normal by an axis number than by a
          three component vector.

        .. note: This method will also work if any or both of P and n have
          a shape (ncoords,3), where ncoords is the total number of points
          in the :class:`Coords`. This allows to project each point on an
          individual plane.
        ), or by

        Returns: a :class:`Coords` with same shape as original, with all the
        points projected on the specified plane(s).
        """
        if type(n) is int:
            x = self.copy()
            x[...,n] = P[n]
            return x
        
        n = normalize(Coords(n).reshape(-1,3))
        x = self.reshape(-1,3)
        x =  - dotpr(n,(x-P))
        return self + outer(x,n).reshape(self.shape)


    def projectOnSphere(self,radius=1.,center=[0.,0.,0.]):
        """Project :class:`Coords` on a sphere.

        The default sphere is a unit sphere at the origin.
        The center of the sphere should not be part of the :class:`Coords`.
        """
        d = self.distanceFromPoint(center)
        s = radius / d
        f = self - center
        for i in range(3):
            f[...,i] *= s
        f += center
        return f


    def projectOnCylinder(self,radius=1.,dir=0,center=[0.,0.,0.]):
        """Project :class:`Coords` on a cylinder with axis parallel to a global axis.

        The default cylinder has its axis along the x-axis and a unit radius.
        No points of the :class:`Coords` should belong to the axis..
        """
        d = self.distanceFromLine(center,unitVector(dir))
        s = radius / d
        c = resize(asarray(center),self.shape)
        c[...,dir] = self[...,dir]
        f = self - c
        axes = range(3)
        del axes[dir]
        for i in axes:
            f[...,i] *= s
        f += c
        return f


    def projectOnSurface(self,S,n,ignore_errors=False):
        """Project the Coords on a triangulated surface.

        The points of the Coords are projected in the direction of the
        vector n onto the surface S. 

        Parameters:

        - `S`: TriSurface: any triangulated surface
        - `n`: int or vector: specifies the direction of the projection
        - `ignore_errors`: if True, projective lines not cutting the
          surface will result in NaN values. The default is to raise an error.

        If successful, a Coords with the same structure as the
        input is returned.
        """
        x = self.reshape(-1,3)
        # Create planes through x in direction n
        # WE SHOULD MOVE THIS TO arraytools?
        from plugins.geomtools import anyPerpendicularVector
        v1 = anyPerpendicularVector(n)
        v2 = cross(n,v1)
        # Create set of cuts with set of planes
        print type(S)
        cuts = [ S.intersectionWithPlane(xi,v1) for xi in x ]
        # cut the cuts with second set of planes
        points = [ c.toFormex().intersectionWithPlane(xi,v2) for c,xi in zip(cuts,x) ]
        if ignore_errors :
            points = [ p for p in points if p.shape[0] > 0 ]
        else:
            npts = [ p.shape[0] for p in points ]
            if min(npts) == 0:
                print npts
                raise RuntimeError,"Some line has no intersection point"
        # find the points closest to self
        points = [ p.closestToPoint(xi) for p,xi in zip(points,x) ]
        return Coords.concatenate(points)


    # Extra transformations implemented by plugins

    def isopar(self,eltype,coords,oldcoords):
        """Perform an isoparametric transformation on a Coords.

        This is a convenience method to transform a Coords object through
        an isoparametric transformation. It is equivalent to::

          Isopar(eltype,coords,oldcoords).transform(self)

        See :mod:`plugins.isopar` for more details.
        """
        from plugins.isopar import Isopar
        return Isopar(eltype,coords,oldcoords).transform(self)


    def transformCS(self,currentCS,initialCS=None):
        """Perform a CoordinateSystem transformation on the Coords.

        This method transforms the Coords object by the transformation that
        turns the initial CoordinateSystem into the currentCoordinateSystem.

        currentCS and initialCS are CoordinateSystem or (4,3) shaped Coords
        instances. If initialCS is None, the global (x,y,z) axes are used.

        E.g. the default initialCS and currentCS equal to::

           0.  1.  0.
          -1.  0.  0.
           0.  0.  1.
           0.  0.  0.

        result in a rotation of 90 degrees around the z-axis.

        This is a convenience function equivalent to:: 

          self.isopar('tet4',currentCS,initialCS)
        """
        # This is currently implemented using isopar, but could
        # obviously also be done using affine
        return self.isopar('tet4',currentCS,initialCS)


    def addNoise(self,rsize=0.1,asize=0.0):
        """Add random noise to a Coords.

        A random amount is added to eacho individual coordinate in the Coords.
        The difference of any coordinate from its original value will
        not be maximally ``asize + rsize * self.sizes().max()``. The default
        is to set it to 0.1 times the geometrical size of the structure.
        """
        max = asize + rsize * self.sizes().max()
        return self + randomNoise(self.shape,-max,+max)
        

############################################################################
    #
    #   Transformations that change the shape of the Coords array
    #
 

    def replicate(self,n,dir=0,step=None):
        """Replicate a Coords n times with fixed step in any direction.

        Returns a Coords object with shape `(n,) + self.shape`, thus having
        an extra first axis.
        Each component along the axis 0 is equal to the previous component
        translated over `(dir,step)`, where `dir` and `step` are
        interpreted just like in the :meth:`translate` method.
        The first component along the axis 0 is identical to the
        original Coords.
        """
        n = int(n)
        if type(dir) is int:
            dir = unitVector(dir)
        dir = Coords(dir,copy=True)
        if step is not None:
            dir *= step 
        f = resize(self,(n,)+self.shape)
        for i in range(1,n):
            f[i] += i*dir
        return Coords(f)
    
 
    def split(self):
        """Split the coordinate array in blocks along first axis.

        The result is a sequence of arrays with shape self.shape[1:].
        Raises an error if self.ndim < 2.
        """
        if self.ndim < 2:
            raise ValueError,"Can only split arrays with dim >= 2"
        return [ self[i] for i in range(self.shape[0]) ]


    def fuse(self,nodesperbox=1,shift=0.5,rtol=1.e-5,atol=1.e-5,repeat=True):
        """Find (almost) identical nodes and return a compressed set.

        This method finds the points that are very close and replaces them
        with a single point. The return value is a tuple of two arrays:

        - the unique points as a :class:`Coords` object with shape (npoints,3)
        - an integer (nnod) array holding an index in the unique
          coordinates array for each of the original nodes. This index will
          have the same shape as the pshape() of the coords array.

        The procedure works by first dividing the 3D space in a number of
        equally sized boxes, with a mean population of nodesperbox.
        The boxes are numbered in the 3 directions and a unique integer scalar
        is computed, that is then used to sort the nodes.
        Then only nodes inside the same box are compared on almost equal
        coordinates, using the numpy allclose() function. Two coordinates are
        considered close if they are within a relative tolerance rtol or
        absolute tolerance atol. See numpy for detail. The default atol is
        set larger than in numpy, because pyformex typically runs with single
        precision.
        Close nodes are replaced by a single one.

        Running the procedure once does not guarantee to find all close nodes:
        two close nodes might be in adjacent boxes. The performance hit for
        testing adjacent boxes is rather high, and the probability of separating
        two close nodes with the computed box limits is very small.
        Therefore, the most sensible way is to run the procedure twice, with
        a different shift value (they should differ more than the tolerance).
        Specifying repeat=True will automatically do this.
        """
        if self.size == 0:
            # allow empty coords sets
            return self,array([],dtype=Int).reshape(self.pshape())
        
        if repeat:
            # Aplly twice with different shift value
            coords,index = self.fuse(nodesperbox,shift,rtol,atol,repeat=False)
            coords,index2 = coords.fuse(nodesperbox,shift+0.25,rtol,atol,repeat=False)
            index = index2[index]
            return coords,index

        # This is the single pass
        x = self.points()
        nnod = x.shape[0]
        # Calculate box size
        lo = array([ x[:,i].min() for i in range(3) ])
        hi = array([ x[:,i].max() for i in range(3) ])
        sz = hi-lo
        esz = sz[sz > 0.0]  # only keep the nonzero dimensions
        if esz.size == 0:
            # All points are coincident
            x = x[:1]
            e = zeros(nnod,dtype=int32)
            return x,e

        vol = esz.prod()
        nboxes = nnod / nodesperbox # ideal total number of boxes
        boxsz = (vol/nboxes) ** (1./esz.shape[0])
        nx = (sz/boxsz).astype(int32)
        # avoid error message on the global sz/nx calculation
        errh = seterr(all='ignore')
        dx = where(nx>0,sz/nx,boxsz)
        seterr(**errh)
        #
        nx = array(nx) + 1
        ox = lo - dx*shift # origin :  0 < shift < 1
        # Create box coordinates for all nodes
        ind = floor((x-ox)/dx).astype(int32)
        # Create unique box numbers in smallest direction first
        o = argsort(nx)
        val = ( ind[:,o[2]] * nx[o[2]] + ind[:,o[1]] ) * nx[o[1]] + ind[:,o[0]]
        # sort according to box number
        srt = argsort(val)
        # rearrange the data according to the sort order
        val = val[srt]
        x = x[srt]
        # now compact
        # make sure we use int32 (for the fast fuse function)
        # Using int32 limits this procedure to 10**9 points, which is more
        # than enough for all practical purposes
        x = x.astype(float32)
        val = val.astype(int32)
        tol = float32(max(abs(rtol*self.sizes()).max(),atol))
        nnod = val.shape[0]
        flag = ones((nnod,),dtype=int32)   # 1 = new, 0 = existing node
        # new fusing algorithm
        sel = arange(nnod).astype(int32)      # replacement unique node nr
        misc._fuse(x,val,flag,sel,tol)     # fuse the close points
        x = x[flag>0]          # extract unique nodes
        s = sel[argsort(srt)]  # and indices for old nodes
        return (x,s.reshape(self.shape[:-1]))


    def match(self,coords,**kargs):
        """Match points form another Coords object.

        This method finds the points from `coords` that coincide with
        (or are very close to) points of `self`.

        Parameters:

        - `coords`: a Coords object
        - `**kargs`: keyword arguments that you want to pass to the
          :meth:`fuse` method.

        This method works by concatenating the serialized point sets of
        both Coords and then fusing them.
        
        Returns:

        - `matches`: an Int array with shape (nmatches,2)
        - `coords`: a Coords with the fused coordinate set
        - `index`: an index with the position of each of the serialized
          points of the concatenation in the fused coordinate set. To find
          the index of the points of the orginal coordinate sets, split
          this index at the position self.npoints() and reshape the resulting
          parts to `self.pshape()`, resp. `coords.pshape()`.
          
        """
        x = Coords.concatenate([self.points(),coords.points()])
        c,e = x.fuse(**kargs)
        e0,e1 = e[:self.npoints()],e[self.npoints():]
        matches = matchIndex(e0,e1)
        return matches


    def append(self,coords):
        """Append coords to a Coords object.

        The appended coords should have matching dimensions in all
        but the first axis.

        Returns the concatenated Coords object, without changing the current.

        This is comparable to :func:`numpy.append`, but the result
        is a :class:`Coords` object, the default axis is the first one
        instead of the last, and it is a method rather than a function.
        """
        return Coords(append(self,coords,axis=0))
            

    @classmethod
    def concatenate(clas,L,axis=0):
        """Concatenate a list of :class:`Coords` object.

        All :class:`Coords` object in the list L should have the same shape
        except for the length of the specified axis.
        This function is equivalent to the numpy concatenate, but makes
        sure the result is a :class:`Coords` object,and the default axis
        is the first one instead of the last.
        """
        return Coords(concatenate(atleast_2d(*L),axis=axis))


    @classmethod
    def fromstring(clas,fil,sep=' ',ndim=3,count=-1):
        """Create a :class:`Coords` object with data from a string.

        This convenience function uses the :func:`numpy.fromstring`
        function to read coordinates from a string.

        `fil`: a string containing a single sequence of float numbers separated
        by whitespace and a possible separator string.

        `sep`: the separator used between the coordinates. If not a space,
        all extra whitespace is ignored. 

        `ndim`: number of coordinates per point. Should be 1, 2 or 3 (default).
        If 1, resp. 2, the coordinate string only holds x, resp. x,y
        values.

        `count`: total number of coordinates to read. This should be a multiple
        of 3. The default is to read all the coordinates in the string.
        count can be used to force an error condition if the string
        does not contain the expected number of values.

        The return value is  Coords object.
        """
        x = fromstring(fil,dtype=Float,sep=sep,count=count)
        if count > 0 and x.size != count :
            raise RuntimeError,"Number of coordinates read: %s, expected %s!" % (x.size,count)
        if x.size % ndim != 0 :
            raise RuntimeError,"Number of coordinates read: %s, expected a multiple of %s!" % (x.size,ndim)
        return Coords(x.reshape(-1,ndim))


    @classmethod
    def fromfile(clas,fil,**kargs):
        """Read a :class:`Coords` from file.

        This convenience function uses the numpy fromfile function to read
        the coordinates from file.
        You just have to make sure that the coordinates are read in order
        (X,Y,Z) for subsequent points, and that the total number of
        coordinates read is a multiple of 3.
        """
        x = fromfile(fil,dtype=Float,**kargs)
        if x.size % 3 != 0 :
            raise RuntimeError,"Number of coordinates read: %s, should be multiple of 3!" % x.size
        return Coords(x.reshape(-1,3))

    
    def interpolate(self,X,div):
        """Create interpolations between two :class:`Coords`.

        Parameters:

        - `X`: a :class:`Coords` with same shape as `self`.
        - `div`: a list of floating point values, or an int. If an int
          is specified, a list with (div+1) values for `div` is created
          by dividing the interval [0..1] into `div` equal distances.

        Returns:

        A :class:`Coords` with an extra (first) axis, containing the
        concatenation of the interpolations of `self` and `X` at all
        values in `div`.
        Its shape is (n,) + self.shape, where n is the number of values
        in `div`.
        
        An interpolation of F and G at value v is a :class:`Coords` H where
        each coordinate Hijk is obtained from:  Fijk = Fijk + v * (Gijk-Fijk).
        Thus, X.interpolate(Y,[0.,0.5,1.0]) will contain all points of
        X and Y and all points with mean coordinates between those of X and Y.

        F.interpolate(G,n) is equivalent with
        F.interpolate(G,arange(0,n+1)/float(n))
        """
        if self.shape != X.shape:
            raise RuntimeError,"`X` should have same shape as `self`"
        if type(div) == int:
            div = arange(div+1) / float(div)
        else:
            div = array(div).ravel()
        return self + outer(div,X-self).reshape((-1,)+self.shape)


    # Convenient shorter notations
    rot = rotate
    trl = translate
    rep = replicate


    # Deprecated functions

    # BV: removed in 0.8.4
    ## @deprecated(reflect)
    ## def mirror(*args,**kargs):
    ##     return reflect(*args,**kargs)


    def actor(self,**kargs):
        """_This allows a Coords object to be drawn directly"""

        if self.npoints() == 0:
            return None
        
        from gui.actors import GeomActor
        from formex import Formex
        return GeomActor(Formex(self.reshape(-1,3)),**kargs)


class CoordinateSystem(Coords):
    """A CoordinateSystem defines a coordinate system in 3D space.

    The coordinate system is defined by and stored as a set of four points:
    three endpoints of the unit vectors along the axes at the origin, and
    the origin itself as fourth point.

    The constructor takes a (4,3) array as input. The default constructs
    the standard global Cartesian axes system:

      1.  0.  0.
      0.  1.  0.
      0.  0.  1.
      0.  0.  0.
    """
    def __new__(clas,coords=None,origin=None,axes=None):
        """Initialize the CoordinateSystem"""
        if coords is None:
            coords = eye(4,3)
            if axes is not None:
                coords[:3] = axes
            if origin is not None:
                coords += origin
        else:
            coords = checkArray(coords,(4,3),'f','i')
        coords = Coords.__new__(clas,coords)
        return coords


    def origin(self):
        """Return the origin of the CoordinateSystem."""
        return Coords(self[3])


    def axes(self):
        """Return the axes of the CoordinateSystem."""
        return Coords(self[:3]-self[3])


    def actor(self,**kargs):
        """_This allows a CoordinateSystem object to be drawn directly."""
        from gui.actors import AxesActor
        return AxesActor(self,**kargs)



# Creating special coordinate sets

def origin():
    """Return a single point with coordinates [0.,0.,0.].

    Returns:
      A :class:`Coords` object with shape(3,) holding three zero coordinates.
    """
    return Coords(zeros((3),dtype=Float))


def sweepCoords(self,path,origin=[0.,0.,0.],normal=0,upvector=2,avgdir=False,enddir=None,scalex=None,scaley=None):
    """ Sweep a Coords object along a path, returning a series of copies.

    origin and normal define the local path position and direction on the mesh.
    
    At each point of the curve, a copy of the Coords object is created, with
    its origin in the curve's point, and its normal along the curve's direction.
    In case of a PolyLine, directions are pointing to the next point by default.
    If avgdir==True, average directions are taken at the intermediate points
    avgdir can also be an array like sequence of shape (N,3) to explicitely set the 
    the directions for ALL the points of the path
    
    Missing end directions can explicitely be set by enddir, and are by default
    taken along the last segment.
    enddir is a list of 2 array like values of shape (3). one of the two can also be an empty list
    If the curve is closed, endpoints are treated as any intermediate point,
    and the user should normally not specify enddir.
    
    At each point of the curve, the original Coords object can be scaled in x
    and y direction by specifying scalex and scaley. The number of values
    specified in scalex and scaly should be equal to the number of points on
    the curve.

    The return value is a sequence of the transformed Coords objects.
    """
    points = path.coords
    if isinstance(avgdir,bool):
        if avgdir:
            directions = path.avgDirections()
        else:
            directions = path.directions()
    else:
        directions=asarray(avgdir).reshape(len(avgdir),-1)

    missing = points.shape[0] - directions.shape[0]
    if missing == 1:
        lastdir = (points[-1] - points[-2]).reshape(1,3)
        directions = concatenate([directions,lastdir],axis=0)
    elif missing == 2:
        lastdir = (points[-1] - points[-2]).reshape(1,3)
        firstdir = (points[1] - points[0]).reshape(1,3)
        directions = concatenate([firstdir,directions,lastdir],axis=0)

    if enddir:
        for i,j in enumerate([0,-1]):
            if enddir[i]:
                directions[j] = Coords(enddir[i])

    directions = normalize(directions)

    if type(normal) is int:
        normal = unitVector(normal)

    if type(upvector) is int:
        upvector = Coords(unitVector(upvector))
        
    if scalex is not None:
        if len(scalex) != points.shape[0]:
            raise ValueError,"The number of scale values in x-direction differs from the number of copies that will be created."
    else:
        scalex = ones(points.shape[0])
        
    if scaley is not None:
        if len(scaley) != points.shape[0]:
            raise ValueError,"The number of scale values in y-direction differs from the number of copies that will be created."
    else:
        scaley = ones(points.shape[0])
    
    base = self.translate(-Coords(origin))
    sequence = [ base.scale([scx,scy,1.]).rotate(vectorRotation(normal,d,upvector)).translate(p)
                 for scx,scy,d,p in zip(scalex,scaley,directions,points)
                 ]
        
    return sequence


##############################################################################
#
#  Testing
#
#  Some of the docstrings above hold test examples. They should be careflly 
#  crafted to test the functionality of the Formex class.
#
#  Ad hoc test examples during development can be added to the test() function
#  below.
#
#  python formex.py
#    will execute the docstring examples silently. 
#  python formex.py -v
#    will execute the docstring examples verbosely.
#  In both cases, the ad hoc tests are only run if the docstring tests
#  are passed.
#

if __name__ == "__main__":

    def testX(X):
        """Run some tests on:class:`Coords` X."""

        def prt(s,v):
            """Print a statement 's = v' and return v"""
            if isinstance(v,ndarray):
                sep = '\n'
            else:
                sep = ' '
            print("%s =%s%s" % (s,sep,v))
            return v

        prt("###################################\nTests for Coords X",X)

        # Info
        prt("points",X.points())
        prt("pshape",X.pshape())
        prt("npoints",X.npoints())
        prt("y",X.y())
        prt("bbox",X.bbox())
        prt("center",X.center())
        prt("centroid",X.centroid())
        prt("sizes",X.sizes())
        prt("dsize",X.dsize())
        prt("bsphere",X.bsphere())
        prt("distanceFromPlane",X.distanceFromPlane([0.,0.,1.],[0.,0.,1.]))
        prt("distanceFromLine",X.distanceFromLine([0.,0.,1.],[0.,0.,1.]))
        prt("distanceFromPoint",X.distanceFromPoint([0.,0.,1.]))
        prt("test",X.test(dir=1,min=0.5,max=1.5))
        prt("test2",X.test(dir=[1.,1.,0.],min=[0.,0.5,0.],max=[0.,1.5,0.]))

        # Transforms
        prt("X_scl",X.scale(2,False))
        prt("X",X)
        prt("X_scl",X.scale(2,True))
        prt("X",X)
        prt("X_scl2",X.scale([0.5,1.,0.]))
        prt("X_trl",X.copy().translate(0,6))
        prt("X_trl2",X.translate([10.,100.,1000.]))
        prt("X_rot",X.rotate(90.))
        prt("X_rot2",X.rotate(90.,0))
        
        Y=prt("Y = X_reflect",X.reflect(1,2))
        prt("X_bbox",X.bbox())
        prt("Y_bbox",Y.bbox())
        prt("(X+Y)bbox",bbox([X,Y]))
        Z = X.copy().reflect(1,1.5).translate(1,2)
        prt("X",X)
        prt("Y",Y)
        prt("Z",Z)
        G = Coords.concatenate([X,Z,Y,Z],axis=0)
        prt("X+Z+Y+Z",G)
        return
    

    def test():
        """Run the tests.

        This is intended for tests during development and can be
        changed at will.
        """
        testX(Coords([[1,0,0],[0,1,0]]))
        testX(Coords([[[0,0,0],[1,0,0]],[[0,1,0],[1,1,0]]]))
        testX(Coords([1,0,0]))
        try:
            testX(Coords())
        except:
            print "Some test(s) failed for an empty Coords"
            print "But that surely is no surprise"
        return

        
        
    f = 0

    #import doctest, formex
    #f,t = doctest.testmod(formex)

    if f == 0:
        test()

### End
