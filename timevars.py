#!python  -u

import math
import random

class Magazine(object):
    """Simulates an ammo magazine that holds N bullets and takes time 
    to deliver and to restock. """
    def __init__(self, maxCapacity, deliveryResetSec, loadResetSec, initialHold = 0):
        super(Magazine, self).__init__()
        self.maxCapacity = maxCapacity
        self.deliveryResetSec = deliveryResetSec
        self.loadResetSec = loadResetSec
        self.currHold = initialHold

        self.sinceDelivery = 0.
        self.sinceLoad = 0.

    def update(self, dt):
        self.sinceDelivery += dt
        self.sinceLoad += dt

    def empty(self):
        return self.currHold == 0

    def full(self):
        return self.currHold == self.maxCapacity

    def isDeliverReady(self):
        if self.currHold > 0 and self.sinceDelivery >= self.deliveryResetSec:
            return True
        else:
            return False

    def isLoadReady(self):
        if self.currHold < self.maxCapacity and self.sinceLoad >= self.loadResetSec:
            return True
        else:
            return False

    def deliver(self):
        if self.currHold == 0:  
            raise Exception("Tried to deliver from empty magazine")

        if self.sinceDelivery < self.deliveryResetSec:
            raise Exception("Tried to deliver from magazine too quickly")

        self.currHold -= 1
        self.sinceDelivery = 0.

    def load(self):
        if self.currHold == self.maxCapacity:
            raise Exception("Tried to load an already full magazine")

        if self.sinceLoad < self.loadResetSec:
            raise Exception("Tried to load  magazine too quickly")

        self.currHold += 1
        self.sinceLoad = 0.


        


class Blinker(object):
    """ On/Off/On/Off """
    def __init__(self, period):
        super(Blinker, self).__init__()
        self.switchTime = period/2.
        self.timeSinceSwitch = 0.0
        self.state = True

    def start(self):
        self.running = True

    def update(self, dt):
        self.timeSinceSwitch += dt
        if self.timeSinceSwitch >= self.switchTime:
            self.state = not self.state
            self.timeSinceSwitch -= self.switchTime

    def isOn(self):
        return self.state


class PLInterpolator(object):
    """ Piece-wise linear interpolator. Not really a time-varying value,
        this seems like a sensible place to put it. 
    """
    
    # Change init to take *nodes, not a single nodes List!
    # (API change. Will need to update client code)
    def __init__(self, nodes):
        super(PLInterpolator, self).__init__()
        self.nodes = nodes

    def __call__(self, t):
        # User is responsible for keeping t within range.
        i = 0
        while self.nodes[i][0] < t:
            i += 1

        # t between nodes i-1 and i
        a = self.nodes[i-1]
        b = self.nodes[i]
        t = (t - a[0]) / (b[0] - a[0])
        v = a[1] + t * (b[1] - a[1])
        return v

    def shift(self, xShift, yShift):
        for i, pt in enumerate(self.nodes):
            self.nodes[i] = (pt[0]+xShift, pt[1]+yShift)

class CountUpTimer(object):
    ''' Just keeps a running total of time elapsed since starting'''
    def __init__(self, running=False):
        self.timeAlive = 0.0
        self.running = running
        self.alive = True

    def start(self):
        self.running = True

    def update(self, dt):
        if not self.running:
            return

        self.timeAlive += dt

    def time(self):
        return self.timeAlive

    def done(self):
        return False

class CountDownTimer(object):
    ''' Simple countdown timer'''
    def __init__(self, lifetime, running=False):
        self.lifetime = lifetime
        self.timeAlive = 0.0
        self.running = running
        self.alive = True

    def start(self):
        self.running = True

    def update(self, dt):
        if not self.running:
            return

        self.timeAlive += dt
        if self.timeAlive > self.lifetime:
            self.alive = False

    def done(self):
        return self.running and not self.alive


class Shaker(object):
    def __init__(self, lifetime, _range):
        self.lifetime = lifetime
        self.range = _range
        self.timeAlive = 0.0
        self.alive = True

    def update(self, dt):
        self.timeAlive += dt
        if self.timeAlive > self.lifetime:
            self.alive = False

    def getValue(self):
        return self.range * (2. * random.random() - 1.)

class Shaker2(object):
    def __init__(self, lifetime, rangeSpace, rangeAngle):
        self.x = Shaker(lifetime, rangeSpace)
        self.y = Shaker(lifetime, rangeSpace)
        self.rangeAngle = rangeAngle
        self.alive = True

    def update(self, dt):
        self.x.update(dt)
        self.y.update(dt)
        self.alive = self.x.alive

    def getValue(self):
        return (self.x.getValue(), self.y.getValue())

    def getAngle(self):
        return self.rangeAngle * random.random()


class LinearMotion(object):
    def __init__(self, x, vx):
        self.sx = x
        self.vx = vx

    def update(self, dt):
        self.sx += self.vx * dt

    def wrap( self, lo, hi):
        if self.sx > hi:
            self.sx -= (hi-lo)
        elif self.sx < lo:
            self.sx += (hi-lo)

    def bounce( self, lo, hi):
        if self.sx > hi:
            self.sx = 2*hi - self.sx
            self.vx *= -1.0
        elif self.sx < lo:
            self.sx = 2*lo - self.sx
            self.vx *= -1.0

    def getValue(self):
        return self.sx

class LinearMotion2(object):
    def __init__(self, x, y, vx, vy):
        super(self.__class__, self).__init__()
        self.x = LinearMotion(x,vx)
        self.y = LinearMotion(y,vy)

    def update(self, dt):
        self.x.update(dt)
        self.y.update(dt)

    def wrap( self, lox, hix, loy, hiy):
        self.x.wrap(lox, hix)
        self.y.wrap(loy, hiy)

    def bounce( self, lox, hix, loy, hiy):
        self.x.bounce(lox, hix)
        self.y.bounce(loy, hiy)

    def getValue(self):
        return (self.x.getValue(), self.y.getValue())

class ThrustMotionWithDrag(object):
    """docstring for Motion"""
    def __init__(self, x, y):
        super(self.__class__, self).__init__()
        self.sx = x
        self.sy = y

        self.vx = 0
        self.vy = 0

        self.ax = 0
        self.ay = 0

    def setDrag(self, drag):
        self.drag = drag

    def position(self):
        #return (round(self.sx), round(self.sy))
        return (self.sx, self.sy)

    def velocity(self):
        #return (round(self.sx), round(self.sy))
        return (self.vx, self.vy)

    def set(self, position=None, velocity=None, acceleration=None):
        # Used if outside interactions (e.g. bouncing off wall) over-ride internal state
        if position:
            self.sx = position[0]
            self.sy = position[1]

        if velocity:
            self.vx = velocity[0]
            self.vy = velocity[1]

        if acceleration:
            self.ax = acceleration[0]
            self.ay = acceleration[1]

    def update(self, dt):
        vLen = math.sqrt(self.vx * self.vx + self.vy * self.vy)

        self.vx += self.ax * dt
        self.vy += self.ay * dt

        self.sx += self.vx * dt
        self.sy += self.vy * dt

        self.ax = -self.vx * vLen * self.drag * dt
        self.ay = -self.vy * vLen * self.drag * dt


    def thrust(self, dvx, dvy):
        self.vx += dvx
        self.vy += dvy

    #def setForce(self, ax, ay):
    #    self.ax = ax
    #    self.ay = ay

    def wrap( self, w, h):
        if self.sx > w:
            self.sx -= w
        elif self.sx < 0:
            self.sx += w

        if self.sy > h:
            self.sy -= h
        elif self.sy < 0:
            self.sy += h

    def bounce( self, w, h):
        if self.sx > w:
            self.sx = 2*w - self.sx
            self.vx *= -1.0
        elif self.sx < 0:
            self.sx = -self.sx
            self.vx *= -1.0

        if self.sy > h:
            self.sy = 2*h - self.sy
            self.vy *= -1.0
        elif self.sy < 0:
            self.sy = -self.sy
            self.vy *= -1.0


class TargetTracker(object):
    """
    Value tracks target, with damping
    User should set value and target before using, but we don't enforce that
    with the c'tor.
    """
    def __init__(self, pull, drag):
        super(TargetTracker, self).__init__()
        # Parameters
        self.pull = pull
        self.drag = drag

        # Target value
        self.target = None

        # State: value and d_value/dt
        self.value  = None         # consider this publicly readable.
        self.dvalue = 0.0

        disc = self.drag * self.drag - 4.0 * self.pull
        d_over_two = -self.drag / 2.0
        if disc >= 0:
            r = math.sqrt(disc)/2.0

            #print "r1", d_over_two - r
            #print "r2", d_over_two + r
        else:
            #print d_over_two, "+-", math.sqrt(-disc)/2.0, "i"
            pass
        

    def initVals(self, value, target):
        self.value = value
        self.target = target

    def setTarget(self, target):
        self.target = target

    def setValue(self, value):
        self.value = value


    def update(self, dt):
        # Returns updated value as a convenience
        f = self.pull*(self.target - self.value) - self.drag * self.dvalue
        a = f * dt
        self.dvalue += a * dt
        self.value  += self.dvalue * dt
        return self.value


class AngleTargetTracker(TargetTracker):
    ''' Just a TargetTracker that handles wrapping angles. '''

    def __init__(self, pull, drag):
        super(AngleTargetTracker, self).__init__(pull, drag)


    def setTarget(self, target):
        #print self.value, self.target
        prd = math.floor((target - self.value + 180.0)/360.0)
        if prd != 0:
            self.target = target - 360. * prd
        else:
            self.target = target


class TimeAverage(object):
    """Keeps a windowed decaying time average of a quantitiy"""
    def __init__(self, decayRate, initVal=0.0):
        super(TimeAverage, self).__init__()
        self.decayRate = decayRate
        self.updateRate = 1.0 - decayRate
        self.currValue = initVal

    def update(self, val):
        # Note: this isn't time dependent. For the window to be a consistent time
        # interval we should include a dt, but we'll assume the dt's are pretty
        # constant and punt the issue.

        self.currValue = self.updateRate * val + self.decayRate * self.currValue 
        return self.currValue
        
    def value(self):
        return self.currValue


class TimeAverage2(object):
    def __init__(self, decayRate, initValX=0.0, initValY=0.0):
        super(TimeAverage2, self).__init__()
        self.x = TimeAverage(decayRate, initValX)
        self.y = TimeAverage(decayRate, initValY)

    def update(self, xVal, yVal):
        self.x.update(xVal)
        self.y.update(yVal)

        return (self.x.currValue, self.y.currValue)

    def value(self):
        return (self.x.currValue, self.y.currValue)


def clamp(low, val, high):
    if val >= high:
        return high
    if val <= low:
        return low
    return val


def wrap( val, lo, hi):
    t = (val - lo)/(hi - lo)
    t = t - math.floor(t)
    return lo + t * (hi - lo)
