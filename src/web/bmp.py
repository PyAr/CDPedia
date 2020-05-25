# Basado en bmp 0.2, de Paul McGuire, October, 2003

"""
bmp.py - module for constructing simple BMP graphics files

 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import base64
import pickle
import bz2

from math import ceil, hypot
from io import StringIO

BOGUS_W = 87
BOGUS_H = 16

BOGUS_LABEL = pickle.loads(bz2.decompress(base64.b64decode(b'''
QlpoOTFBWSZTWako/W0AAy/dgAAQAEF/4AAgIAREAGAIKD0GC8ESfF2+57b2yt3a7l3geKbCGqap
ADTTIFNVT9SGElN+qqoBoAJTyVFQzVGIG1J6SYIGCFR6qgDTQS28Wyyb4igKtikvU7/Hhx0xej8Q
wbo1Ig6zMMaFEuWSbSRFiXMdQ7Y08Vl1ROkPeFSamOA5mGzAJNm8usHDW8O3PO7mu5WFVm8qwjN0
KZBmrktw4aQraHC8yMEKNBrdwuBPMadgDh0DQ8OjSNZGgGiDaAdS71u7Rkuahk2MeT0yGSLGYW06
tzM2HFFDpENGBF0hVBWEdAr4BEwNExAIGgi1izr14SEZEwugsCpHDCBnCERNmSFe47hHkgQeHZwq
zzMmc58ETOVt5mEW0O7K4iLnE0OW8GWseYpDNzMzby2MF1Ussky8nKQkhd3YRw0ZXbs41Vq1sg9v
bXNGeG5a1rRQsVrOceoiJAYceC8zrZe3BR4XVcNubA+DaYVQquXRMsxxUnhsylKu3ip1kEORmnq3
YgLkqsOjcwBTm6Axc5fCLnHlKbFRFIVa5d5SE2YJJl7s3BJzMqTmK9fEkdnENRWWi5xVj2peSXFr
krbmV1TswNOdkm9tbW4MvbruFV0jQamQgUDslIMptNF+fTa7xfR3vlHm99988cRKilotVUNUb2O8
al4aAvG7qmaoUXuWzL058m7vOxMJK3ke+Gd5HtBnnbDmts0RUJr3HnleRMkltZGp3rZ8wxiNjbzy
PPCXGxRSUNzKbiq/kCABA9+nB/N7fv1mZt3cwiQfEEiTAEG7/PZpJ0gwQEpdSKNVNVMEyqVKWk2y
N3VOobf6zZuv32cnKdbZVUBaHok8dPcvcBI0BJwTyUKKT3SKR79eh1VVVVVVwLNNP/XGZv2+6LvK
q8wQgSQTBgwMVuZlOBDIAJEzMQbZKV9TkJ77jZfne/bVNPaMs/BTUVfIi9+vTcXITKDubcQwJRub
cEw7bdRYwEBA3O7q5ZlbbdExbbuEkItt0wwFbZEUMQDEEFtoQNZ+zO+bVVG5Nu0kmKNVKIIGnZlc
lp++rg8dsn2rQbug3zvPc8fWcpIQXduhkWGAtt0Mqw8tiq608dtBtONoLXyvPl1ptFKRA66HfPqy
4JBIJJFVSiIBIRZG3vTdrj77cxk+qp9ra6qSDgwSQDckyTBBnmhBmVVJGFGIqRW+HzeW13eq7a93
au5qCAAgolov7fvcDbd3cDSCYIBEDKyyVQqIEyJ4OE8DXBWrFUsx/H4Ot0+aw+jCTL93nPfT5tq2
CAIN4VCru73d3dg0+W/dweJ1eYAcAkNLGnKcwIIBmULltvFWptvWOpX7F8qPl1pfDW1XoD+SAvCw
YKcbeGoNqh3c2JZ2+3KFeXBmBk5aKTgQ224DbaSx0KbTBSXIStG0479mVDivzTJ+3AljoVynoi7t
klkXPZGiRrlk2vhx9Pt+OtLeGgwaDYNoLQAB70kj6l3veqPc9zdGP13fyPk2XgP24H8anfDQ6zXh
g0G3Cvc7uulQBCS+JTBIERUwa+9hw6H76puXL8KMr6/N0ijyKCvPKqKfD7+eY2223cYdsbbA2wG2
qqq/H1fj37Lb89yqAFVaTENtuJlttJsXSdAturkLiM3w34L3n9aLTjoH7J8gAAAB7veEkAAAADnO
c55PMUQQwTRJVCMQ001EiRCqRBMQwkQ0JJRQSkEiwEqyMlJQDESJNUrSMUhICwhEQRIwKSgSEESl
BCDCSyUCTEKEASEKyJDEKCl+/woDLarX/F3JFOFCQqSj9bQ=''')))


def shortToString(i):
  hi = (i & 0xff00) >> 8
  lo = i & 0x00ff
  return chr(lo) + chr(hi)

def longToString(i):
  hi = (int(i) & 0x7fff0000) >> 16
  lo = int(i) & 0x0000ffff
  return shortToString(lo) + shortToString(hi)


class Color(object):
  """class for specifying colors while drawing BitMap elements"""
  __slots__ = [ 'red', 'grn', 'blu' ]
  __shade = 32
  
  def __init__( self, r=0, g=0, b=0 ):
    self.red = r
    self.grn = g
    self.blu = b

  def __setattr__(self, name, value):
    if hasattr(self, name):
      raise AttributeError("Color is immutable")
    else:
      object.__setattr__(self, name, value)

  def __str__( self ):
    return "R:%d G:%d B:%d" % (self.red, self.grn, self.blu )
    
  def __hash__( self ):
    return ( ( int(self.blu) ) + 
              ( int(self.grn) <<  8 ) + 
              ( int(self.red) << 16 ) )
  
  def __eq__( self, other ):
    return (self is other) or (self.toLong == other.toLong)

  def toLong( self ):
    return self.__hash__()
    
  def fromLong( l ):
    b = l & 0xff
    l = l >> 8
    g = l & 0xff
    l = l >> 8
    r = l & 0xff
    return Color( r, g, b )
  fromLong = staticmethod(fromLong)

class BitMap(object):
  """class for drawing and saving simple Windows bitmap files"""
  
  def __init__(self, width, height, bkgd=Color(240, 240, 240),
    frgd=Color(200, 200, 200)):
    self.wd = int( ceil(width) )
    self.ht = int( ceil(height) )
    self.bgcolor = 0
    self.fgcolor = 1
    self.palette = []
    self.palette.append( bkgd.toLong() )
    self.palette.append( frgd.toLong() )
    self.setDefaultPenColor()

    tmparray = [ self.bgcolor ] * self.wd
    self.bitarray = [ tmparray[:] for i in range( self.ht ) ]
    self.currentPen = 1
    self.fontName = "%s-%d-%s" % ( "none", 0, "none" )
    
  def setDefaultPenColor( self ):
    self.currentPen = self.fgcolor
    
  def setPenColor( self, pcolor ):
    oldColor = self.currentPen
    # look for c in palette
    pcolornum = pcolor.toLong()
    try:
      self.currentPen = self.palette.index( pcolornum )
    except ValueError:
      if len( self.palette ) < 256 :
        self.palette.append( pcolornum )
        self.currentPen = len( self.palette ) - 1
      else:
        self.currentPen = self.fgcolor
    
    return Color.fromLong( self.palette[oldColor] )

  def plotPoint( self, x, y ):
    if ( 0 <= x < self.wd and 0 <= y < self.ht ):
      x = int(x)
      y = int(y)
      self.bitarray[y][x] = self.currentPen
      
  def plotPointByColor( self, x, y, color ):
    self.setPenColor(color)
    self.plotPoint(x, y)
      
  def drawRect( self, x, y, wid, ht, fill=False ):
    x = int(x)
    y = int(y)
    cury = y

    # subtract one for line width
    wid -= 1
    ht -= 1
    
    self.drawLine( x, y, x+wid, y )
    if fill:
      cury = y
      while cury < y+ht:
        self.drawLine( x, cury, x+wid, cury )
        cury += 1
    else:
      self.drawLine( x, y, x, y+ht )
      self.drawLine( x+wid, y, x+wid, y+ht )
    self.drawLine( x, y+ht, x+wid, y+ht )
    
  def bresLine(x,y,x2,y2):
    """Bresenham line algorithm"""
    steep = 0
    coords = []
    dx = int(abs(x2 - x)+0.5)
    if (x2 - x) > 0: 
      sx = 1
    else: 
      sx = -1
    dy = int(abs(y2 - y)+0.5)
    if (y2 - y) > 0: 
      sy = 1
    else: 
      sy = -1
    if dy > dx:
      steep = 1
      x,y = y,x
      dx,dy = dy,dx
      sx,sy = sy,sx
    dx2 = dx*2
    dy2 = dy*2
    d = dy2 - dx
    for i in range(0,dx):
      coords.append( (x,y) )
      while d >= 0:
        y += sy
        d -= dx2
      x += sx
      d += dy2

    if steep: #transpose x's and y's
      coords = [ (c[1],c[0]) for c in coords ]
    
    coords.append( (x2,y2) )
      
    return coords
  bresLine = staticmethod( bresLine )

  def drawLine( self, x1, y1, x2, y2 ):
    # special checks for vert and horiz lines
    if ( x1 == x2 ):
      if 0 <= x1 < self.wd:
        if ( y2 < y1 ): 
          y1,y2 = y2,y1
        cury = max( y1, 0 )
        maxy = min( y2, self.ht-1 )
        while cury <= maxy :
          self.plotPoint( x1, cury )
          cury += 1
      return
      
    if ( y1 == y2 ):
      if ( 0 <= y1 < self.ht ):
        if ( x2 < x1 ):
          x1,x2 = x2,x1
        curx = max( x1, 0 )
        maxx = min( x2, self.wd-1 )
        while curx <= maxx:
          self.plotPoint( curx, y1 )
          curx += 1
      return

    for pt in BitMap.bresLine(x1, y1, x2, y2):
      self.plotPoint( pt[0], pt[1] )
  
  def drawLines( self, lineSegs ):
    for x1,y1,x2,y2 in lineSegs:
      self.drawLine( x1, y1, x2, y2 )

 
  def saveFile(self, f):
    # write bitmap header
    f.write( "BM" )
    f.write( longToString( 54 + 256*4 + self.ht*self.wd ) )   # DWORD size in bytes of the file
    f.write( longToString( 0 ) )    # DWORD 0
    f.write( longToString( 54 + 256*4 ) )    # DWORD offset to the data
    f.write( longToString( 40 ) )    # DWORD header size = 40
    f.write( longToString( self.wd ) )    # DWORD image width
    f.write( longToString( self.ht ) )    # DWORD image height
    f.write( shortToString( 1 ) )    # WORD planes = 1
    f.write( shortToString( 8 ) )    # WORD bits per pixel = 8
    f.write( longToString( 1 ) )    # DWORD compression = 1=RLE8
    f.write( longToString( self.wd * self.ht ) )    # DWORD sizeimage = size in bytes of the bitmap = width * height
    f.write( longToString( 0 ) )    # DWORD horiz pixels per meter (?)
    f.write( longToString( 0 ) )    # DWORD ver pixels per meter (?)
    f.write( longToString( 256 ) )    # DWORD number of colors used = 256
    f.write( longToString( len(self.palette) ) )    # DWORD number of "import colors = len( self.palette )

    # write bitmap palette 
    for clr in self.palette:
      f.write( longToString( clr ) )
    for i in range( len(self.palette), 256 ):
      f.write( longToString( 0 ) )
    
    # write pixels
    pixelBytes = 0
    for row in self.bitarray:
      rleStart = 0
      curPixel = rleStart+1
      while curPixel < len(row):
        if row[curPixel] != row[rleStart] or curPixel-rleStart == 255:
          # write out from rleStart thru curPixel-1
          f.write( chr( curPixel-rleStart ) )
          f.write( chr( row[rleStart] ) )
          pixelBytes += 2
          rleStart = curPixel
        else:
          pass
        curPixel += 1
          
      # write out last run of colors
      f.write( chr( curPixel-rleStart ) )
      f.write( chr( row[rleStart] ) ) 
      pixelBytes += 2
      
      # end of line code
      f.write( chr(0) )
      f.write( chr(0) )
      pixelBytes += 2
    
    # end of bitmap code
    f.write( chr(0) )
    f.write( chr(1) )
    pixelBytes += 2

    # now fix sizes in header
    f.seek(2)
    f.write( longToString( 54 + 256*4 + pixelBytes ) )   # DWORD size in bytes of the file
    f.seek(34)
    f.write( longToString( pixelBytes ) )   # DWORD size in bytes of the file

class BogusBitMap(BitMap):
    def __init__(self, width, height):
        super(BogusBitMap, self).__init__(width, height)
        self.drawRect(0, 0, width, height)
        self.drawRect(1, 1, width - 2, height - 2)
        self.drawLine(0, height, width, 0)
        self.drawLine(0, height - 1, width, -1)
        self.drawLine(0, height - 2, width, -2)
        if width > BOGUS_W + 6 and height > BOGUS_H + 6:
            self.stampBogus((width - BOGUS_W) / 2, (height - BOGUS_H) / 2)

    def stampBogus(self, x, y):
        for p in BOGUS_LABEL:
            self.plotPointByColor(x + p[0], y + p[1], Color(p[2], p[2], p[2]))

    @property
    def data(self):
        buffer = StringIO()
        self.saveFile(buffer)
        return buffer.getvalue()
