#!python  -u
#!/c/Python27/python.exe  -u

import os
import sys

import pyglet
import pyglet.gl as gl
import pyglet.window.mouse as mouse
import pyglet.window.key as key
import pyglet.font.ttf

import random
import math

import timevars as tv
#import vector as v

import xsect

gApp = None
gAssets = None


# Define the application class

class Application(object):
    """
    Application maybe with multiple windows. Should be a Singleton.
    Does little for now but it's where communication between / coordination
    of multiple windows would happen.
    """
    def __init__(self, windowOpts):
        super(Application, self).__init__()

        joysticks = pyglet.input.get_joysticks()
        if len(joysticks) > 0:
            js = joysticks[0]
            js.open()
        else:
            js = None

        #windowOpts = {'width': 1200, 'height': 500}
        #windowOpts = {'fullscreen': True}

        self.window = GameWindow(js, **windowOpts)

    def update(self, dt):
        self.window.update(dt)

class WindowProps(object):
    """Properties of a GameWindow, suitable for passing around without
        passing the full window."""
    
    def __init__(self):
        pass

class GameWindow(pyglet.window.Window):
    """A single window with a game taking place inside it"""
    
    def __init__(self, joystick, **kwargs):

        super(GameWindow, self).__init__(**kwargs)        
        
        if not self.fullscreen:
            self.set_location(20,35)

        self.set_vsync(True)
        self.set_mouse_visible(False)

        self.joystick = joystick

        props = WindowProps()
        w = props.windowWidth     = self.width
        h = props.windowHeight    = self.height
        self.props = props

        # We need to keep references to batched sprites or they get garbage collected!
        self.sprites = [] 

        self.gameElements = GameElements(props)
        self.gameElements.populateGame( gAssets )

        self.score = Score()

        maxSpeed = 200

        self.zombies = []

        self.runner = Runner(w//2, h//2,        maxSpeed)
        self.zombies.append(Zombie( 100, h//2, 1.05 * maxSpeed))
        self.zombies.append(Zombie( 600, h//2, 1.05 * maxSpeed))

        self.grassBatch = pyglet.graphics.Batch()

        grass = self.tileRegion(self.grassBatch, gAssets.getImage('grass'), (0,w), (0,h))
        for g in grass:
            g.opacity = 180

        self.wallImgBatch = pyglet.graphics.Batch()
        self.wallPolygons = xsect.PolygonList()
        brk = gAssets.getImage('brick')

        self.addWall( (400,450), (320,600))
        self.addWall( (450,900), (550,600))
        self.addWall( (850,900), (400,600))


        self.runner = Runner(530, 400,        maxSpeed)

        # Window border
        self.wallPolygons.add(xsect.Polygon((0,0),(w,0),(0,0)))
        self.wallPolygons.add(xsect.Polygon((0,h),(w,h),(0,h)))
        self.wallPolygons.add(xsect.Polygon((0,0),(0,0),(0,h)))
        self.wallPolygons.add(xsect.Polygon((w,0),(w,0),(w,h)))


        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)

        # I think extending Window automatically has this as a handler
        #self.push_handlers(self.on_key_press)

    def addWall(self, xRange, yRange):
        brk = gAssets.getImage('brick')
        self.tileRegion(self.wallImgBatch, brk, xRange, yRange)

        x0,x1 = xRange
        y0,y1 = yRange

        p = xsect.Polygon(
            (x0,y0),
            (x1,y0),
            (x1,y1),
            (x0,y1)
            )

        self.wallPolygons.add(p)

    def tileRegion(self, batch, image, xRange, yRange):
        # adds required tiles to batch
        # returns list of tiles created
        tileList = []

        x = xRange[0]
        while x < xRange[1]:

            y = yRange[0]
            while y < yRange[1]:
                w = min(image.width, xRange[1] - x)
                h = min(image.height, yRange[1] - y)

                if w < image.width or h < image.height:
                    usableImg = image.get_region(x=0, y=0, width=w, height=h)
                else:
                    usableImg = image

                sp = pyglet.sprite.Sprite(usableImg, x, y, batch=batch)
                tileList.append(sp)
                
                # Always save a copy to stop rogue garbage collection
                self.sprites.append(sp) 

                y += image.height

            x += image.width

        return tileList

    def on_key_press(self, symbol, modifiers):
        #print "GameWindow.on_key_press", symbol
        if self.keys[key.Q]:
            pyglet.app.exit()        
        
    def update(self, dt):
        g = self.gameElements

        # Elements that evolve pretty much by themselves.
        g.update(dt)

        for z in self.zombies:
            z.setTarget(self.runner.xPos, self.runner.yPos)
            z.update(dt, self.wallPolygons)


        # Use controls to update the ship.
        if self.joystick is not None:
            self.joystickUpdate(dt)
        else:
            self.keyboardUpdate(dt)


    def joystickUpdate(self, dt):
        js = self.joystick
        self = self.gameElements

        g.runner.shift(3*js.rx, -3*js.ry)


    def keyboardUpdate(self, dt):
        # Use keyboard to control ship
        g = self.gameElements
        dx, dy = 0, 0

        if self.keys[key.LEFT]:
            dx = -1
        if self.keys[key.RIGHT]:
            dx = +1
        
        if self.keys[key.UP]:
            dy = +1
        if self.keys[key.DOWN]:
            dy = -1

        self.runner.update(dt, (dx, dy), self.wallPolygons)


    def on_draw(self):
        grey = 0.9
        gl.glClearColor(grey, grey, grey, 0.0)
        gl.glEnable( gl.GL_BLEND)
        gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        gl.glPushMatrix()

        # I don't really know what the direction conventions for glTranslate are,
        # so the minus signs are from experimenting.
        #gl.glTranslatef(-self.viewportOrigin[0], -self.viewportOrigin[1], 0.0)
        
        self.clear()
        self.grassBatch.draw()
        self.wallImgBatch.draw()

        g = self.gameElements

        # Should I be pushing most of this code into GameElements?

        self.runner.on_draw()
        for z in self.zombies:
            z.on_draw()

        
        gl.glPopMatrix()
        #g.score.draw()

class GameAssets(object):
    """ Loads images, sounds, etc. from files and holds them as pyglet-compatible
        objects. """

    def __init__(self):
        super(GameAssets, self).__init__()

    def loadAssets(self):
        self.images = {}

        #self.loadStdImage('green.png', 'runner')
        self.loadStdImage('foob.png', 'runner')
        self.loadStdImage('zombie-sprite-right.png', 'zombie-right')
        self.loadStdImage('zombie-sprite-left.png', 'zombie-left')
        #self.loadStdImage('foob2.png', 'zombie')

        img = self.loadStdImage('Grass-036-10pct.jpg', 'grass')
        img.anchor_x = 0
        img.anchor_y = 0

        img = self.loadStdImage('Red-Brick-Wall-Tile-Textures-560x373.jpg', 'brick')
        img.anchor_x = 0
        img.anchor_y = 0

        #self.pew = pyglet.resource.media('pew4.mp3', streaming=False)

        # Get this font by specifying font_name='Orbitron', bold=True
        #fontFile = 'Orbitron Bold.ttf'
        #pyglet.resource.add_font(fontFile)


    def loadStdImage(self, fileName, tag):
        # Loads the image and puts the anchor in the center.
        # You can re-set the center if that default isn't right.
        #imgDir = './themes/default/images'
        img = pyglet.resource.image(fileName)
        img.anchor_x = img.width//2
        img.anchor_y = img.height//2
        self.images[tag] = img
        return img

    def getImage(self, tag):
        return self.images[tag]

class GameElements(object):
    """Holds all the elements that make up a game"""
    def __init__(self, props):
        super(GameElements, self).__init__()
        self.props = props
        
    def populateGame(self, assets):
        pass


    def update(self, dt):
        pass

class Runner(pyglet.sprite.Sprite):

    def __init__(self, x, y, maxSpeed):
        super(Runner, self).__init__(gAssets.getImage('runner'), x,y)
        # These are floating point numbers for motion simulation. 
        # Assign them to the underlying Sprite's x & y before drawing.
        self.xPos = x
        self.yPos = y
        self.maxSpeed = maxSpeed

        self.motion = tv.ThrustMotionWithDrag( x, y)
        self.motion.setDrag(0.05)
        self.thrustPower = 400.0    # units?


    def getRadius(self):
        return self.width//2

    def getVelocity(self):
        return self.motion.velocity()

    def on_draw(self):
        self.x = self.xPos
        self.y = self.yPos
        self.draw()

    def getDesiredMove(self, dt, (dx,dy)):
        x, y = self.motion.position()
        start = (x,y)

        ds = self.thrustPower * dt
        self.motion.thrust( ds * dx, ds * dy)
        self.motion.update(dt)
        x, y = self.motion.position()
        end = (x,y)

        return start, end

    def getDesiredMove1(self, dt, (dx,dy)):
        start = (self.xPos, self.yPos)
        end = (self.xPos + dt * self.maxSpeed * dx, self.yPos + dt * self.maxSpeed * dy)

        return start, end

    def update(self, dt, (dx,dy), walls):
        start, end = self.getDesiredMove(dt, (dx, dy))
        move = xsect.Move(start, end)
        velocity = None

        # There is a risk of an infinite loop here.
        # Not sure how to prevent it. XXX
        while move:
            hits = xsect.disc_move_x_polygon_list(self.getRadius(), move, walls)

            if not hits:
                self.xPos = move.endPoint[0]
                self.yPos = move.endPoint[1]

                if velocity:
                    self.motion.set(position=move.endPoint, velocity=velocity)
                return


            # There was a hit
            hit = hits[0]
            move = move.submove(hit.moveParameter - 0.0001, 1.0)
            velocity = self.getVelocity()

            move, velocity = xsect.bounceMoveOffHit( move, hit, velocity=velocity, rebound=0.35)


#class Zombie(pyglet.sprite.Sprite):
class Zombie(object):

    def __init__(self, x, y, maxSpeed):
        super(Zombie, self).__init__()
        self.spriteRight = pyglet.sprite.Sprite(gAssets.getImage('zombie-right'))
        self.spriteLeft  = pyglet.sprite.Sprite(gAssets.getImage('zombie-left'))

        self.activeSprite = self.spriteRight
        
        self.xPos = x
        self.yPos = y

        self.xTarget = x
        self.yTarget = y

        self.maxSpeed = maxSpeed
        self.criticalDistance = 200

        self.stepTime = 10000.0
        self.stepCycleTime = 0.4
        self.stepDir = None
        self.stepSpeed = None
        self.stepSpeedFactorCurve = tv.PLInterpolator((
            (0.0,0.3),
            (self.stepCycleTime * 0.3, 1.7),
            (self.stepCycleTime * 0.6, 1.1),
            (self.stepCycleTime, 1.3),
            (1000.0, 1.3)
        ))

        #self.rotation = 180.0

    def getRadius(self):
        return self.activeSprite.width//2

    def setTarget( self, x, y):
        self.xTarget = x
        self.yTarget = y

    def on_draw(self):
        self.activeSprite.x = self.xPos
        self.activeSprite.y = self.yPos
        self.activeSprite.draw()

    def update(self, dt, walls):
        self.stepTime += dt
        if self.stepTime > self.stepCycleTime:
            # Calculate new move
            self.stepTime = 0.0
            self.calculateStep()

        #start, end = self.getDesiredMove(dt)
        start, end = self.getDesiredStepMove(dt)

        move = xsect.Move(start, end)
        velocity = None

        # There is a risk of an infinite loop here.
        # Not sure how to prevent it. XXX
        while move:
            hits = xsect.disc_move_x_polygon_list(self.getRadius(), move, walls)

            if not hits:
                self.xPos = move.endPoint[0]
                self.yPos = move.endPoint[1]

                #if velocity:
                #    self.motion.set(position=move.endPoint, velocity=velocity)
                return


            # There was a hit
            hit = hits[0]
            move = move.submove(hit.moveParameter - 0.0001, 1.0)
            #velocity = self.getVelocity()

            move, velocity = xsect.bounceMoveOffHit( move, hit, velocity=velocity, rebound=0.0)


    def getDistanceSpeedFactor(self, d):
        t = d/self.criticalDistance
        return 1.0/(1.0 + t*t)

    def calculateStep(self):
        target = (self.xTarget - self.xPos, self.yTarget - self.yPos)
        self.stepDir, d = xsect.polarizeVector(target)
        self.stepSpeed = self.maxSpeed * self.getDistanceSpeedFactor(d)

        if target[0] < 0:
            self.activeSprite = self.spriteLeft
            self.activeSprite.rotation = (-180.0/math.pi) * math.atan2(target[1], target[0])-180.0
        else:
            self.activeSprite = self.spriteRight
            self.activeSprite.rotation = (-180.0/math.pi) * math.atan2(target[1], target[0])

    def getDesiredStepMove(self, dt):
        inStepFactor = self.stepSpeedFactorCurve(self.stepTime)
        t = self.stepSpeed * inStepFactor * dt
        step = (t*self.stepDir[0], t*self.stepDir[1])
        return (self.xPos, self.yPos), (self.xPos+step[0], self.yPos+step[1])

    def getDesiredMove(self, dt):
        '''
        p1 = v.Vector(self.xTarget, self.yTarget)
        p2 = v.Vector(self.xPos, self.yPos)
        targetDir = p1-p2
        targetDistance = v.Norm(targetDir)
        '''

        targetDir = xsect.vectorMinus( (self.xTarget, self.yTarget), (self.xPos, self.yPos))
        uVec, targetDistance = xsect.polarizeVector(targetDir)
        
        vel = self.maxSpeed * self.getDistanceSpeedFactor(targetDistance)

        travel = min(targetDistance, vel * dt)
        #try:
        #    uVec = targetDir * (1./targetDistance)
        #except ZeroDivisionError:
        #    uVec = targetDir    # travel is going to be zero anyways

        staggerAngle = random.gauss(0., 30.* math.pi/180.)
        s,c = math.sin(staggerAngle), math.cos(staggerAngle)
        #uVec.x, uVec.y = c*uVec.x + s*uVec.y, -s*uVec.x + c*uVec.y

        return (self.xPos, self.yPos), (self.xPos + travel * uVec.x, self.yPos + travel * uVec.y)



class Score(pyglet.text.Label):
    """docstring for Score"""
    def __init__(self, *args, **kwargs):

        super(Score, self).__init__(
            text="0", font_name='Orbitron',  bold=True, font_size=24,
            anchor_x = "left", anchor_y="bottom",
            color=(255,255,0, 200),
            x=10, y=10)

        self.value = 0
        self.outOf = 0

    def incrOutOf(self, x):
        self.outOf += x
        self.text = "%d / %d" % (self.value, self.outOf)


    def addScore(self, bump):
        self.value += bump
        self.text = "%d / %d" % (self.value, self.outOf)



def update(dt):
    #print "update", dt

    global gApp
    gApp.update(dt)


def uvec(degrees):
    rads = math.pi * degrees / 180.0
    return (math.sin(rads), math.cos(rads))

def getJoystickPolarLeft(js):
    # Note 1: I assume th will just be jittery around the origin.
    # Note 2: It's possible r will go above 1.0. We can normalize r based
    #         on angle here if we want.

    x,y = js.x, js.y
    r2 = x*x + y*y
    th = math.atan2(y,x) * (180.0/math.pi)

    return math.sqrt(r2), th

def getJoystickPolarRight(js):
    x,y = js.rx, js.ry
    r2 = x*x + y*y
    th = math.atan2(y,x) * (180.0/math.pi)

    return math.sqrt(r2), th

def clamp(low, val, high):
    if val >= high:
        return high
    if val <= low:
        return low
    return val

def ray_x_pnt(o, u, p):
    # Returns across, along distances
    d = p-o
    along = v.Dot(u, d)
    proj =  u * along
    perp = d - proj
    return v.Norm(perp), along

def main():
    global gApp
    global gAssets

    if len(sys.argv) > 1 and sys.argv[1] == '-f':
        windowOpts = {'fullscreen': True}
    else:
        windowOpts = {'width': 1000, 'height': 500}

    #pyglet.resource.path = ['images', 'sounds', 'fonts', 
    #    'themes/default/images', 'themes/default/fonts']
    pyglet.resource.path = ['images']
    pyglet.resource.reindex()

    # Create the (few) global object
    gAssets = GameAssets()
    gAssets.loadAssets()

    gApp = Application(windowOpts)


    pyglet.clock.set_fps_limit(60)
    pyglet.clock.schedule_interval(update, 1/60.)

    pyglet.app.run()


if __name__ == '__main__':
    main()

