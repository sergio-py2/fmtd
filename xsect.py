#!python  -u

import math

class Envelope(object):
    """ A rectangular region around a polygon, used for quick disjointness checking"""
    def __init__(self):
        super(Envelope, self).__init__()
        self.xMin = None
        self.xMax = None
        self.yMin = None
        self.yMax = None

    def fromPolygon(self, polygon):
        v = polygon.vertexList[0]
        self.xMin = self.xMax = v[0]
        self.yMin = self.yMax = v[1]

        for v in polygon.vertexList[1:]:
            self.xMin = min(self.xMin, v[0])
            self.xMax = min(self.xMax, v[0])

            self.yMin = min(self.yMin, v[1])
            self.yMax = min(self.yMax, v[1])


class PolygonList(object):
    """ A list of polygons """
    def __init__(self):
        super(PolygonList, self).__init__()
        self.polygons = []

    def add(self, polygon):
        self.polygons.append(polygon)

class Vertex(object):
    """Vertex of a polygon"""
    def __init__(self, pt):
        super(Vertex, self).__init__()
        self.pt = pt

    def coords(self):
        return self.pt
    
class Edge(object):
    """Single edge of a polygon"""
    def __init__(self, startPoint, endPoint):
        super(Edge, self).__init__()
        self.startPoint = startPoint
        self.endPoint = endPoint

        self.direction, self.length = polarizeVector( (
            endPoint[0] - startPoint[0],
            endPoint[1] - startPoint[1]) )

        self.normal = rot90CW(self.direction)

        self.normalDot = dot(self.normal, startPoint)

    def __str__(self):
        return "Edge: %s, %s" % (self.startPoint, self.endPoint)


class Polygon(object):
    """ A single polygon """

    def __init__(self, *vertices):
        # vertexList is a list of pairs
        # vertices must traverse the polygon in a counter-clockwise direction
        super(Polygon, self).__init__()
        self.vertices = [Vertex(v) for v in vertices]
        self.N = len(vertices)

        self.edges = []
        # edge[i] goes from vertex[i] to vertex[i+1]
        for i in range(0, self.N):
            iNext = (i+1) % self.N
            e = Edge(vertices[i], vertices[iNext])
            self.edges.append(e)


class Xsect(object):
    """ Represents a single intersection"""
    TYPE_EDGE, TYPE_VERTEX = 1, 2
    def __init__(self, type):
        super(Xsect, self).__init__()
        self.type = type
        self.moveParameter = -1.0
        self.hitObject = None

class Move(object):
    """ A 2-D move, parameterized from 0.0 to 1.0 """
    def __init__(self, startPoint, endPoint):
        super(Move, self).__init__()
        self.startPoint = startPoint
        self.endPoint = endPoint

        t = vecMinus(endPoint, startPoint)
        self.direction, self.length = polarizeVector(t)

    def atParameter(self, t):
        return lincom(1.0-t, self.startPoint, t, self.endPoint)

    def length(self):
        return self.length

    def submove(self, startParam, endParam):
        return Move( self.atParameter(startParam), self.atParameter(endParam))
        


def disc_move_x_polygon_list(discRadius, move, pList):
    # Returns: List of hits, as Xsect objects
    hits = []
    
    # Get vectors and lengths associated with the move
    t = (move.endPoint[0]-move.startPoint[0], move.endPoint[1]-move.startPoint[1])
    moveDir, moveLen = polarizeVector(t)

    if moveLen == 0.0:
        return hits

    moveNormal = rot90CW(moveDir)
    moveNormalDot = dot(move.startPoint, moveNormal)


    # Check edges
    for p in pList.polygons:
        for e in p.edges:
            # Move crosses offset wall?
            a1 = dot(move.startPoint, e.normal) - e.normalDot - discRadius
            b1 = dot(move.endPoint, e.normal) - e.normalDot - discRadius
            #print "a1", a1, "b1", b1

            if a1 * b1 >= 0:
                continue

            # Check that a1 and b1 aren't very small, which
            # corresponds to moving right along side the edge.
            epsilon = 0.0000000001
            if abs(a1) < epsilon or abs(b1) < epsilon:
                # I'm not expecting this to happen, so notify if it does.
                print "Rejected hit as extremely near-edge motion"
                continue

            # Move parallel to wall
            if a1 - b1 == 0.:
                continue

            # Offset wall crosses path of move?
            t = discRadius*dot(e.normal, moveNormal) - moveNormalDot
            a2 = dot(moveNormal, e.startPoint) + t
            b2 = dot(moveNormal, e.endPoint) + t
            #print "a2", a2, "b2", b2

            if a2 * b2 > 0:
                continue

            hit = Xsect(Xsect.TYPE_EDGE)
            hit.hitObject = e
            hit.moveParameter = a1/(a1-b1)
            hits.append(hit)
            #print "Hit edge", hit.moveParameter

        # Check vertices
        for v in p.vertices:
            # First eliminate vertices that are far away from entire move line
            lineToVertex = vecMinus(v.coords(),  move.startPoint)
            lenAlongMove = dot(lineToVertex, move.direction)
            nearestDist2 = dot(lineToVertex, lineToVertex) - lenAlongMove*lenAlongMove

            if nearestDist2 >= discRadius*discRadius:
                continue

            # Calculate parameters along move ('t') that are exactly discRadius from vertex.
            tNearest = lenAlongMove / move.length
            lenToHitpointFromNearest = math.sqrt(discRadius*discRadius - nearestDist2)
            plusMinusT = lenToHitpointFromNearest/move.length

            for t in (tNearest-plusMinusT, tNearest+plusMinusT):
                if t < 0.0 or t > 1.0:
                    continue

                hit = Xsect(Xsect.TYPE_VERTEX)
                hit.hitObject = v
                hit.moveParameter = t
                hits.append(hit)
                #print "Hit vertex", t


    hits.sort(key=lambda h: h.moveParameter)
    return hits

def bounceMoveOffHit( move, hit, rebound = 1.0, velocity = None):
    # Returns move, velocity
    #   where move = resulting move
    #         velocity = transformed velocity
    #
    #   Input move's start point is assumed to be hitting the hit object
    #   Returned velocity is None if input velocity is None

    if hit.type == Xsect.TYPE_VERTEX:
        t = vecMinus(move.startPoint, hit.hitObject.coords())
        normal, _ = polarizeVector(t)
    elif hit.type == Xsect.TYPE_EDGE:
        normal = hit.hitObject.normal

    normalLen = move.length * dot(move.direction, normal)
    pos = lincom(1.0, move.startPoint, -(1.0 + rebound)*normalLen, normal)

    if velocity:
        normalLen = dot(velocity, normal)
        velocity = lincom(1.0, velocity, -(1.0 + rebound)*normalLen, normal)

    return Move(move.startPoint, pos), velocity


def stopDeadAtHit( move, hit, rebound = 1.0, velocity = None):
    # Same interface as bounceMoveOffHit
    return Move(move.startPoint, move.startPoint), (0.0, 0.0)


# Vector utilities
def polarizeVector(v):
    r = math.sqrt(v[0]*v[0] + v[1]*v[1])
    if r > 0.:
        return (v[0]/r,v[1]/r), r
    else:
        return (1,0), 0.

def rot90CW(u):
    return (u[1], -u[0])

def dot(u,v):
    return u[0]*v[0] + u[1]*v[1]

def norm(u):
    return math.sqrt(u[0]*u[0] + u[1]*u[1])

def norm2(u):
    return u[0]*u[0] + u[1]*u[1]

def vecMinus(u,v):
    return (u[0]-v[0], u[1]-v[1])

def lincom(a, u, b, v):
    return (a*u[0]+b*v[0], a*u[1]+b*v[1])
