#!python  -u

import math
import colorsys

import pyglet
import pyglet.gl as gl

import timevars as tv


class CountDownTimer(object):
    """docstring for CountDownTimer"""
    ST_STOPPED, ST_RUNNING_UP, ST_RUNNING_DOWN = 1,2,3

    def __init__(self, seconds):
        super(CountDownTimer, self).__init__()
        self.state = CountDownTimer.ST_STOPPED
        self.readyToStart = False
        self.timeDone = False

        self.startTime = seconds
        self.currTime = 0.0

        self.rCurve = tv.PLInterpolator(((0,255), (0.1*seconds, 255), (0.5*seconds,0), (seconds,0)))
        self.gCurve = tv.PLInterpolator(((0,0), (0.1*seconds, 48), (0.5*seconds,255), (seconds,255)))
        self.bCurve = tv.PLInterpolator(((0,0), (seconds/2.0, 0), (seconds,0)))
        self.hueCurve = tv.PLInterpolator((
            (0,12), 
            (0.04 * seconds, 12), 
            (0.12 * seconds, 60),
            (0.20 * seconds, 60),
            (0.33 * seconds, 140),
            (seconds,140)))

        self.lightnessCurve = tv.PLInterpolator((
            (0, 50),
            (0.20 * seconds, 50),
            (0.33 * seconds, 30),
            (seconds, 30)
            ))

        # hsl(140, 100%, 30%) green
        # hsl(60, 100%, 50%) yellow
        # hsl(12, 100%, 50%) red

        self.arcGranularityDeg = 6

        self.radius = 90
        self.ringWidth = 4

        self.makeRing()

        self.tickBatch = pyglet.graphics.Batch()
        self.addTicks(self.tickBatch, (2,7), range(0,60))
        self.addTicks(self.tickBatch, (3,10), [15, 25, 35, 45, 55, 5])
        self.addTicks(self.tickBatch, (4,15), [10, 20, 30, 40, 50, 60])

        self.textBatch = pyglet.graphics.Batch()
        for i in range (5, 61, 5):
            self.addNumberLabel( self.textBatch, i)


        self.hand = pyglet.graphics.vertex_list(3,
            ('v2f', (-3,-9, 3,-9, 0,88)),
            ('c3B', [255,0,0] * 3)
            )

        self.zeroMark = pyglet.graphics.vertex_list(4,
            ('v2f', (
                -0.5,0.0, 
                 0.5,0.0, 
                 -0.5,89.0,
                 0.5, 89.0 )),
            ('c3B', [1,1,1] * 4)
            )


        self.sweep = None
        self.makeSweep()

    def isStopped(self):
        return self.state == CountDownTimer.ST_STOPPED

    def startRunUp(self):
        self.state = CountDownTimer.ST_RUNNING_UP
        self.currTime = 0.0

    def startCountDown(self):
        self.state = CountDownTimer.ST_RUNNING_DOWN
        self.currTime = self.startTime

    def makeRing(self):
        r = self.radius
        halfWidth = self.ringWidth / 2.0
        verts = []
        colors = []

        steps = 60
        steps = int(math.floor(360.0/ self.arcGranularityDeg))

        for step in range(0, steps+1):
            angle = step * (2*math.pi)/steps
            c, s = math.cos(angle), math.sin(angle)
            
            verts += [(r-halfWidth) * c, (r-halfWidth)*s]
            verts += [(r+halfWidth) * c, (r+halfWidth)*s]
            colors += [0,0,0] * 2


        self.ring = pyglet.graphics.vertex_list(2*(steps+1),
            ('v2f', verts),
            ('c3B', colors)
            )

    def addNumberLabel(self, batch, seconds):
        angle = math.pi/180.0 * (90.0 - 6.0 * seconds)
        c, s = math.cos(angle), math.sin(angle)

        distanceFromCenter = self.radius - 25

        self.digit = pyglet.text.Label(
            batch = batch,
            x = distanceFromCenter * c, y = distanceFromCenter * s,
            text=str(seconds), 
            font_name='Orbitron',  bold=True, 
            font_size = 10,
            anchor_x = "center", anchor_y="center", 
            color=(0, 0, 0, 255))

    def addTicks(self, batch, tickDimensions, ticks):
        w,l = tickDimensions
        for tick in ticks:
            angle = math.pi/180.0 * (90.0 - 6.0 * tick)

            r = (math.cos(angle), math.sin(angle))  # vector along tick
            x = (-r[1], r[0])                       # vector across tick
            p = (self.radius * r[0], self.radius * r[1])  # point on edge ring

            batch.add ( 4, gl.GL_QUADS, None,
                ('v2f', (
                    p[0] + w/2.0*x[0], p[1] + w/2.0*x[1],
                    p[0] - w/2.0*x[0], p[1] - w/2.0*x[1],
                    p[0] - w/2.0*x[0] - l*r[0], p[1] - w/2.0*x[1] -l*r[1],
                    p[0] + w/2.0*x[0] - l*r[0], p[1] + w/2.0*x[1] -l*r[1],
                    )),
                ('c3B', [0,0,0] * 4)
                )


    def makeSweep(self):
        radiusCurve = tv.PLInterpolator(( (0,34), (60,42), (120,50)))
        #radiusCurve = tv.PLInterpolator(( (0,10), (60,38), (120,50)))
        #radiusCurve = tv.PLInterpolator(( (0,50), (60,42), (120,34)))
        #radiusCurve = tv.PLInterpolator(( (0,50), (60,50), (120,50)))
        widthCurve  = tv.PLInterpolator(( (0,2),  (120,2)))

        handAngle = self.currTime * 6.0
        handAngle = -handAngle

        verts = []
        colors = []
        n = int(math.floor(self.currTime))
        secs = [self.currTime] + range(n, -1, -1)

        for sec in secs:
            angle = (90.0 - 6.0 * sec)* (math.pi/180.0)
            c, s = math.cos(angle), math.sin(angle)

            r = radiusCurve(sec)
            w = widthCurve(sec)

            hue = self.hueCurve(sec)
            lightness = self.lightnessCurve(sec)
            (red, green, blue) = colorsys.hls_to_rgb(hue/360.0, lightness/100.0, 1.0)



            #red = self.rCurve(sec)
            #green = self.gCurve(sec)
            #blue = self.bCurve(sec)
            #print sec, r, w
            
            verts += [(r-w) * c, (r-w)*s]
            verts += [(r+w) * c, (r+w)*s]
            #colors += [120,120,120] * 2
            colors += [int(255*red),int(255*green),int(255*blue)] * 2

        if self.sweep:
            self.sweep.delete()

        self.sweep = pyglet.graphics.vertex_list(len(verts)//2,
            ('v2f', verts),
            ('c3B', colors)
            )

    def update(self, dt):
        if self.state == CountDownTimer.ST_STOPPED:
            return

        if self.state == CountDownTimer.ST_RUNNING_DOWN:
            #self.currTime -= dt
            self.currTime -= 5*dt
            if self.currTime <= 0.0:
                self.currTime = 0.0            
                self.timeDone = True
            self.makeSweep()

        elif self.state == CountDownTimer.ST_RUNNING_UP:
            self.currTime += 50*dt
            if self.currTime >= self.startTime:
                self.currTime = self.startTime
                self.readyToStart = True
            self.makeSweep()


    def draw(self):
        self.ring.draw(pyglet.gl.GL_QUAD_STRIP)
        self.tickBatch.draw()
        self.textBatch.draw()
        self.zeroMark.draw(pyglet.gl.GL_QUAD_STRIP)
        self.sweep.draw(pyglet.gl.GL_QUAD_STRIP)

        # 60 seconds = 360 deg
        # t = 0 seconds <--> straight up <--> rotation = 0 deg
        handAngle = self.currTime * 6.0

        gl.glPushMatrix()
        gl.glRotatef( -handAngle, 0, 0, 1)
        self.hand.draw(pyglet.gl.GL_TRIANGLES)
        gl.glPopMatrix()

