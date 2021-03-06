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
import countdowntimer

gApp = None
gAssets = None
FPS = 30.0

# Define the application class

# Objects that just hold a bunch of attributes
class Attributes(object):
    pass

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

        self.userInput = Attributes()
        self.userInput.joystick = None
        self.userInput.keys = key.KeyStateHandler()
        self.userInput.mousePosition = (0,0)

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

        #self.runner = Runner(w//2, h//2,        maxSpeed)
        self.zombies.append(Zombie( 100, h//2, maxSpeed))
        self.zombies.append(Zombie( 800, h//2, maxSpeed))

        self.grassBatch = pyglet.graphics.Batch()

        grass = self.tileRegion(self.grassBatch, gAssets.getImage('grass'), (0,w), (0,h))
        for g in grass:
            g.opacity = 180

        self.wallImgBatch = pyglet.graphics.Batch()
        self.wallPolygons = xsect.PolygonList()
        brk = gAssets.getImage('brick')

        #self.addWall( (400,450), (320,600))
        #self.addWall( (450,900), (550,600))
        #self.addWall( (850,900), (400,600))

        #self.addWall( (200,250), (100,400))
        #self.addWall( (600,650), (100,350))

        self.runner = Runner(530, 400, maxSpeed)
        self.countdowntimer = countdowntimer.CountDownTimer(110)

        # Window border
        self.wallPolygons.add(xsect.Polygon((0,0),(w,0)))
        self.wallPolygons.add(xsect.Polygon((w,0),(w,h)))
        self.wallPolygons.add(xsect.Polygon((w,h),(0,h)))
        self.wallPolygons.add(xsect.Polygon((0,h),(0,0)))


        #self.keys = key.KeyStateHandler()
        #self.push_handlers(self.keys)
        self.push_handlers(self.userInput.keys)
        

        # I think extending Window automatically has this as a handler
        #self.push_handlers(self.on_key_press)

        self.push_handlers(self.on_mouse_motion)

    def on_mouse_motion(self, x, y, dx, dy):
        #print "on_mouse_motion", x, y, dx, dy
        self.userInput.mousePosition = (x,y)

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
        if self.userInput.keys[key.Q]:
            pyglet.app.exit()        
        
    def update(self, dt):
        g = self.gameElements
        keys = self.userInput.keys

        # Elements that evolve pretty much by themselves.
        g.update(dt)

        for z in self.zombies:
            z.setTarget(self.runner.xPos, self.runner.yPos)
            z.update(dt, self.wallPolygons)


        # Use controls to update the ship.
        if self.userInput.joystick is not None:
            self.joystickUpdate(dt)
        else:
            self.keyboardUpdate(dt)

        timer = self.countdowntimer
        if keys[key.SPACE]:
            if timer.isStopped():
                timer.startRunUp()
            elif timer.readyToStart:
                timer.startCountDown()

        self.countdowntimer.update(dt)


    def joystickUpdate(self, dt):
        pass

    def keyboardUpdate(self, dt):
        self.runner.update(dt, self.userInput, self.wallPolygons)

    def on_draw(self):
        gl.glEnable( gl.GL_POLYGON_SMOOTH )
        #gl.glHint( gl.GL_POLYGON_SMOOTH_HINT, gl.GL_NICEST ) 
        gl.glHint( gl.GL_POLYGON_SMOOTH_HINT, gl.GL_DONT_CARE ) 

        gl.glEnable( gl.GL_LINE_SMOOTH )

        gl.glEnable(gl.GL_MULTISAMPLE)

        gl.glEnable( gl.GL_BLEND)
        gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        #gl.glBlendFunc( gl.GL_SRC_ALPHA_SATURATE, gl.GL_ONE)

        grey = 0.9
        gl.glClearColor(grey, grey, grey, 0.0)

        gl.glPushMatrix()

        # I don't really know what the direction conventions for glTranslate are,
        # so the minus signs are from experimenting.
        #gl.glTranslatef(-self.viewportOrigin[0], -self.viewportOrigin[1], 0.0)
        
        self.clear()
        #self.grassBatch.draw()
        #self.wallImgBatch.draw()

        g = self.gameElements

        # Should I be pushing most of this code into GameElements?

        self.runner.on_draw()
        for z in self.zombies:
            #z.on_draw()
            pass
        

        gl.glPushMatrix()
        gl.glTranslatef(300, 300, 0.0)
        #gl.glScalef(0.5, 0.5, 0.0)
        self.countdowntimer.draw()
        gl.glPopMatrix()

        
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
        self.loadStdImage('target-32.png', 'target')

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

class Runner(object):

    def __init__(self, x, y, maxSpeed):
        super(Runner, self).__init__()
        self.sprite = pyglet.sprite.Sprite(gAssets.getImage('runner'), x,y)
        self.targetSprite = pyglet.sprite.Sprite(gAssets.getImage('target'))
        # These are floating point numbers for motion simulation. 
        # Assign them to the underlying Sprite's x & y before drawing.
        self.xPos = x
        self.yPos = y
        self.maxSpeed = maxSpeed

        self.motion = tv.ThrustMotionWithDrag( x, y)
        self.motion.setDrag(0.05)
        self.thrustPower = 400.0    # units?

        # Data for moving with mouse position targeting
        self.targetPosition = (0,0)
        self.targetFollower = tv.Follower2D()
        self.targetFollower.setDecayRate(0.9, 0.5, FPS)
        #self.targetFollower.setDecayRate(0.01, 50.0, FPS)

        self.targetVelocityFollower = tv.Follower2D()
        self.targetVelocityFollower.setDecayRate(0.95, 0.3, FPS)
        #self.targetVelocityFollower.setDecayRate(0.5, 1.3, FPS)

    def getRadius(self):
        return self.sprite.width//2

    def getVelocity(self):
        return self.motion.velocity()

    def getPosition(self):
        return (self.xPos, self.yPos)

    def on_draw(self):
        self.sprite.x = self.xPos
        self.sprite.y = self.yPos
        self.sprite.draw()

        self.targetSprite.x = self.targetPosition[0]
        self.targetSprite.y = self.targetPosition[1]
        self.targetSprite.draw()

    def getDesiredMoveSpaceship(self, dt, userInput):
        ''' Using the same motion as spaceship in meteor '''
        x, y = self.motion.position()
        start = (x,y)

        dx, dy = readArrowKeys(userInput.keys)

        ds = self.thrustPower * dt
        self.motion.thrust( ds * dx, ds * dy)
        self.motion.update(dt)
        x, y = self.motion.position()
        end = (x,y)

        return start, end

    def getDesiredMoveBasic(self, dt, userInput):
        ''' Simple constant speed moving '''
        start = (self.xPos, self.yPos)
        dx, dy = readArrowKeys(userInput.keys)

        end = (self.xPos + dt * self.maxSpeed * dx, self.yPos + dt * self.maxSpeed * dy)

        return start, end

    def getDesiredMoveTargeted(self, dt, userInput):
        start = (self.xPos, self.yPos)

        self.targetFollower.setTarget(self.targetPosition)
        self.targetFollower.update(dt)

        end = self.targetFollower.getValue()

        return start, end

    def getDesiredMoveTargetedVelocity(self, dt, userInput):
        start = (self.xPos, self.yPos)

        speed = 0.70 * self.maxSpeed
        keys = userInput.keys
        if keys[key.R]:
            speed = 1.04 * self.maxSpeed


        t = xsect.vecMinus(self.targetPosition, start)
        targetDir, targetDistance = xsect.polarizeVector(t)

        # When position is very near the target (< 1 pixel), direction to move
        # gets crazy, so we'll just jump to the desired position
        if targetDistance < 1:
            end = self.targetPosition
            return start, end

        self.targetVelocityFollower.setTarget( 
            (speed*targetDir[0], speed*targetDir[1]) )

        self.targetVelocityFollower.update(dt)
        velocity = self.targetVelocityFollower.getValue()

        #end = (self.xPos + dt*velocity[0], self.yPos + dt*velocity[1])

        # Don't overshoot when moving near target point
        moveDir, moveDirMax = xsect.polarizeVector(velocity)
        moveDistance = min(moveDirMax*dt, targetDistance)
        end = (self.xPos + moveDistance * moveDir[0], self.yPos + moveDistance * moveDir[1])

        return start, end

    def update(self, dt, userInput, walls):
        self.targetPosition = userInput.mousePosition

        start, end = self.getDesiredMoveTargetedVelocity(dt, userInput)
        move = xsect.Move(start, end)
        velocity = None

        # There is a risk of an infinite loop here.
        # Not sure how to prevent it. XXX
        while move:
            hits = xsect.disc_move_x_polygon_list(self.getRadius(), move, walls)

            if not hits:
                self.xPos = move.endPoint[0]
                self.yPos = move.endPoint[1]
                self.targetFollower.setValue(move.endPoint)

                if velocity:
                    self.motion.set(position=move.endPoint, velocity=velocity)
                return


            # There was a hit
            hit = hits[0]
            move = move.submove(hit.moveParameter - 0.0001, 1.0)
            velocity = self.getVelocity()

            move, velocity = xsect.bounceMoveOffHit( move, hit, velocity=velocity, rebound=0.0)


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
        self.stepSpeedFactorCurve = tv.PLInterpolator(
            (0.0,0.3),
            (self.stepCycleTime * 0.3, 1.0),
            (self.stepCycleTime * 0.7, 0.9),
            (self.stepCycleTime      , 0.8),
            (1000.0, 0.6))

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

def readArrowKeys(keys):
    dx, dy = 0, 0

    if keys[key.LEFT]:
        dx = -1
    if keys[key.RIGHT]:
        dx = +1
    
    if keys[key.UP]:
        dy = +1
    if keys[key.DOWN]:
        dy = -1

    return (dx, dy)

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

    #platform = pyglet.window.get_platform()
    #display = platform.get_default_display()
    #screen = display.get_default_screen()

    #for config in screen.get_matching_configs(gl.Config()):
    #    print config

    #config = pyglet.gl.Config(sample_buffers=1, samples=2)
    #config = pyglet.gl.Config()
    
    if len(sys.argv) > 1 and sys.argv[1] == '-f':
        windowOpts = {'fullscreen': True}
        #windowOpts = {'fullscreen': True, 'config':config}
    else:
        windowOpts = {'width': 1000, 'height': 500}
        #windowOpts = {'width': 1000, 'height': 500, 'config':config}

    #pyglet.resource.path = ['images', 'sounds', 'fonts', 
    #    'themes/default/images', 'themes/default/fonts']
    pyglet.resource.path = ['resources']
    pyglet.resource.reindex()

    # Create the (few) global object
    gAssets = GameAssets()
    gAssets.loadAssets()

    gApp = Application(windowOpts)


    pyglet.clock.set_fps_limit(FPS)
    pyglet.clock.schedule_interval(update, 1/FPS)

    pyglet.app.run()


if __name__ == '__main__':
    main()

