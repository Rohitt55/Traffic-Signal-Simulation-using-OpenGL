from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

FONT_SMALL = GLUT_BITMAP_HELVETICA_12 # type: ignore
FONT_BIG = GLUT_BITMAP_HELVETICA_18 # type: ignore

# Global variables

# Window size
W = 800
H = 600

# Camera position
cam_x = 0.0
cam_y = 6.0
cam_z = 18.0

# Last mouse position (for drag rotation)
last_mx = 0
last_my = 0

# Signal state: 0 = red, 1 = yellow, 2 = green
signal = 2
sig_timer = 0
sig_dur = [120, 40, 120] 

# Toggles
fog_on = True
persp = True

# Camera view presets
view_index = 0
views = [
    {"name": "Front", "x": 0.0, "y": 6.0, "z": 18.0},
    {"name": "Right", "x": 18.0, "y": 6.0, "z": 0.0},
    {"name": "Back", "x": 0.0, "y": 6.0, "z": -18.0},
    {"name": "Left", "x": -18.0, "y": 6.0, "z": 0.0},
    {"name": "Top", "x": 0.0, "y": 20.0, "z": 0.1},
]

# Cars (all move right in one lane, same speed, evenly spaced)
cars = [
    {"x": -25, "z": -1.0, "spd": 0.06, "col": (0.9, 0.15, 0.15), "d": 1},
    {"x": -10, "z": -1.0, "spd": 0.06, "col": (0.15, 0.4, 0.9), "d": 1},
    {"x": 5, "z": -1.0, "spd": 0.06, "col": (0.9, 0.8, 0.1), "d": 1},
    {"x": 20, "z": -1.0, "spd": 0.06, "col": (0.2, 0.8, 0.4), "d": 1},
]


def draw_text(x, y, text, font=None):
    if font is None:
        font = FONT_SMALL
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))


# Midpoint line algorithm
def mp_line(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    glBegin(GL_POINTS)
    while True:
        glVertex2f(x0, y0)
        if abs(x0 - x1) < 1 and abs(y0 - y1) < 1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err = err - dy
            x0 = x0 + sx
        if e2 < dx:
            err = err + dx
            y0 = y0 + sy
    glEnd()


# Midpoint circle algorithm
def mp_circle(cx, cy, r):
    x = 0
    y = r
    d = 1 - r
    glBegin(GL_POINTS)
    while x <= y:
        # 8 symmetric points
        points = [
            (x, y), (y, x), (-x, y), (-y, x),
            (x, -y), (y, -x), (-x, -y), (-y, -x),
        ]
        for px, py in points:
            glVertex2f(cx + px, cy + py)
        x = x + 1
        if d < 0:
            d = d + 2 * x + 1
        else:
            y = y - 1
            d = d + 2 * (x - y) + 1
    glEnd()


# Ground - flat shading
def draw_ground():
    glShadeModel(GL_FLAT)
    glColor3f(0.18, 0.42, 0.15)
    glBegin(GL_QUADS)
    glVertex3f(-30, 0, -15)
    glVertex3f(30, 0, -15)
    glVertex3f(30, 0, 15)
    glVertex3f(-30, 0, 15)
    glEnd()


# Road - smooth shading
def draw_road():
    glShadeModel(GL_SMOOTH)
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-30, 0.01, -2.5)
    glVertex3f(30, 0.01, -2.5)
    glVertex3f(30, 0.01, 2.5)
    glVertex3f(-30, 0.01, 2.5)
    glEnd()
    # Dashed center line
    glColor3f(1, 1, 0.3)
    for i in range(-28, 29, 3):
        glBegin(GL_QUADS)
        glVertex3f(i, 0.02, -0.04)
        glVertex3f(i + 1.5, 0.02, -0.04)
        glVertex3f(i + 1.5, 0.02, 0.04)
        glVertex3f(i, 0.02, 0.04)
        glEnd()


# Traffic signal - glow uses blending
def draw_signal(tx, tz, rot):
    glPushMatrix()
    glTranslatef(tx, 0, tz)
    glRotatef(rot, 0, 1, 0)
    # Pole
    glColor3f(0.35, 0.35, 0.35)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    glutSolidCylinder(0.07, 3.2, 8, 1)
    glPopMatrix()
    # Box
    glShadeModel(GL_FLAT)
    glColor3f(0.12, 0.12, 0.12)
    glPushMatrix()
    glTranslatef(0, 3.2, 0)
    glScalef(0.45, 1.1, 0.35)
    glutSolidCube(1)
    glPopMatrix()
    # Bulb colors (on / off)
    on_colors = [(1, 0.1, 0.1), (1, 1, 0.1), (0.1, 1, 0.1)]
    off_colors = [(0.25, 0.05, 0.05), (0.25, 0.25, 0.05), (0.05, 0.25, 0.05)]
    for i in range(3):
        color = on_colors[i] if i == signal else off_colors[i]
        glColor3f(*color)
        glPushMatrix()
        glTranslatef(0, 3.55 - i * 0.32, 0.13)
        glutSolidSphere(0.1, 10, 10)
        glPopMatrix()
        # Glow for the active bulb
        if i == signal:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(on_colors[i][0], on_colors[i][1], on_colors[i][2], 0.2)
            glPushMatrix()
            glTranslatef(0, 3.55 - i * 0.32, 0.15)
            glutSolidSphere(0.18, 10, 10)
            glPopMatrix()
            glDisable(GL_BLEND)
    glPopMatrix()


# Car - headlights use blending
def draw_car(c):
    glShadeModel(GL_SMOOTH)
    glPushMatrix()
    glTranslatef(c["x"], 0.35, c["z"])
    if c["d"] < 0:
        glRotatef(180, 0, 1, 0)
    # Body
    glColor3f(*c["col"])
    glPushMatrix()
    glScalef(1.6, 0.45, 0.8)
    glutSolidCube(1)
    glPopMatrix()
    # Roof (darker shade of body)
    r, g, b = c["col"]
    glColor3f(r * 0.6, g * 0.6, b * 0.6)
    glPushMatrix()
    glTranslatef(-0.1, 0.35, 0)
    glScalef(0.8, 0.35, 0.7)
    glutSolidCube(1)
    glPopMatrix()
    # Wheels
    glColor3f(0.1, 0.1, 0.1)
    for wx, wz in [(0.45, 0.45), (0.45, -0.45), (-0.45, 0.45), (-0.45, -0.45)]:
        glPushMatrix()
        glTranslatef(wx, -0.15, wz)
        glutSolidSphere(0.1, 8, 8)
        glPopMatrix()
    # Headlights
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1, 1, 0.7, 0.5)
    for hz in [0.25, -0.25]:
        glPushMatrix()
        glTranslatef(0.8, 0, hz)
        glutSolidSphere(0.05, 6, 6)
        glPopMatrix()
    glDisable(GL_BLEND)
    glPopMatrix()


# Car speed near signal: green = full, yellow = slow, red = stop
def speed_factor(c):
    near = -5 < c["x"] < -3
    if not near:
        return 1.0
    if signal == 2:
        return 1.0
    if signal == 1:
        return 0.35
    return 0.0


# HUD - 2D overlay (status, timer, controls)
def draw_hud():
    glDisable(GL_FOG)
    glDisable(GL_DEPTH_TEST)
    # Switch to 2D screen coordinates
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, W, 0, H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    # Signal box border - midpoint line
    bx = 15
    by = H - 90
    glColor3f(0.5, 0.5, 0.5)
    mp_line(bx, by, bx + 50, by)
    mp_line(bx + 50, by, bx + 50, by + 75)
    mp_line(bx + 50, by + 75, bx, by + 75)
    mp_line(bx, by + 75, bx, by)
    # Bulbs - midpoint circle
    cols = [(1, 0.1, 0.1), (1, 1, 0.1), (0.1, 1, 0.1)]
    for i in range(3):
        if i == signal:
            glColor3f(*cols[i])
        else:
            glColor3f(0.2, 0.2, 0.2)
        mp_circle(bx + 25, by + 60 - i * 25, 7)
    # Status text
    labels = ["RED - STOP", "YELLOW - SLOW", "GREEN - GO"]
    glColor3f(1, 1, 1)
    draw_text(75, H - 25, labels[signal], FONT_BIG)
    glColor3f(0.3, 1, 0.3)
    draw_text(75, H - 45, "View: " + views[view_index]["name"])
    # Timer bar
    prog = sig_timer / sig_dur[signal]
    glColor3f(0.25, 0.25, 0.25)
    glBegin(GL_QUADS)
    glVertex2f(75, H - 65)
    glVertex2f(250, H - 65)
    glVertex2f(250, H - 55)
    glVertex2f(75, H - 55)
    glEnd()
    bar_cols = [(0.9, 0.2, 0.2), (0.9, 0.9, 0.2), (0.2, 0.9, 0.2)]
    glColor3f(*bar_cols[signal])
    glBegin(GL_QUADS)
    glVertex2f(75, H - 65)
    glVertex2f(75 + 175 * prog, H - 65)
    glVertex2f(75 + 175 * prog, H - 55)
    glVertex2f(75, H - 55)
    glEnd()
    # Controls list
    glColor3f(0.9, 0.9, 0.3)
    draw_text(15, 110, "=== CONTROLS ===")
    glColor3f(0.85, 0.85, 0.85)
    draw_text(15, 95, "Left Click       : Change Signal")
    draw_text(15, 80, "Scroll Up/Down   : Zoom In/Out")
    draw_text(15, 65, "Mouse Drag       : Rotate Camera")
    draw_text(15, 50, "Arrow Keys       : Move Camera")
    draw_text(15, 35, "V / B            : Next / Prev View")
    draw_text(15, 20, "F:Fog  P:Projection  R:Reset")
    # Back to 3D
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


# Draw the whole scene
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    # Projection: perspective or orthographic
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    if persp:
        gluPerspective(50, W / H, 0.1, 80)
    else:
        glOrtho(-12, 12, -8, 8, 0.1, 80)
    # Camera
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(cam_x, cam_y, cam_z, 0, 0, 0, 0, 1, 0)
    # Fog
    if fog_on:
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_EXP2)
        glFogfv(GL_FOG_COLOR, [0.45, 0.5, 0.55, 1])
        glFogf(GL_FOG_DENSITY, 0.025)
    else:
        glDisable(GL_FOG)
    draw_ground()
    draw_road()
    draw_signal(-3, -3, 0)
    for c in cars:
        draw_car(c)
    draw_hud()
    glutSwapBuffers()


# Keyboard keys
def keyboard(key, x, y):
    global fog_on, persp, cam_x, cam_y, cam_z, view_index
    if key == b'f':  # toggle fog
        fog_on = not fog_on
    elif key == b'p':  # toggle projection
        persp = not persp
    elif key == b'r':  # reset to current view
        v = views[view_index]
        cam_x, cam_y, cam_z = v["x"], v["y"], v["z"]
    elif key == b'v':  # next view
        view_index = (view_index + 1) % len(views)
        v = views[view_index]
        cam_x, cam_y, cam_z = v["x"], v["y"], v["z"]
    elif key == b'b':  # previous view
        view_index = (view_index - 1) % len(views)
        v = views[view_index]
        cam_x, cam_y, cam_z = v["x"], v["y"], v["z"]
    glutPostRedisplay()


# Arrow keys move the camera
def special(key, x, y):
    global cam_x, cam_y
    if key == GLUT_KEY_LEFT:
        cam_x = cam_x - 0.4
    elif key == GLUT_KEY_RIGHT:
        cam_x = cam_x + 0.4
    elif key == GLUT_KEY_UP:
        cam_y = cam_y + 0.4
    elif key == GLUT_KEY_DOWN:
        cam_y = cam_y - 0.4
    glutPostRedisplay()


# Mouse click and scroll
def mouse(btn, state, x, y):
    global signal, sig_timer, cam_z
    if state != GLUT_DOWN:
        return
    if btn == GLUT_LEFT_BUTTON:  # change signal
        signal = (signal - 1) % 3
        sig_timer = 0
    elif btn == 3:  # scroll up = zoom in
        cam_z = max(5, cam_z - 1.0)
    elif btn == 4:  # scroll down = zoom out
        cam_z = min(35, cam_z + 1.0)
    glutPostRedisplay()


# Drag to rotate the camera
def motion(x, y):
    global cam_x, cam_y, last_mx, last_my
    cam_x = cam_x + (x - last_mx) * 0.04
    cam_y = cam_y - (y - last_my) * 0.04
    last_mx, last_my = x, y
    glutPostRedisplay()


def passive(x, y):
    global last_mx, last_my
    last_mx, last_my = x, y


# Animation loop: switch signal and move cars
def timer(v):
    global signal, sig_timer
    sig_timer = sig_timer + 1
    # Auto switch 
    if sig_timer >= sig_dur[signal]:
        signal = (signal - 1) % 3
        sig_timer = 0
    GAP = 3.0  
    for c in cars:
        new_x = c["x"] + c["spd"] * c["d"] * speed_factor(c)
       
        for other in cars:
            if other is c:
                continue
            dist = (other["x"] - new_x) * c["d"]
            if 0 < dist < GAP:
                new_x = c["x"]  # hold position
                break
        c["x"] = new_x
        if c["x"] > 30:
            c["x"] = -30
        if c["x"] < -30:
            c["x"] = 30
    glutPostRedisplay()
    glutTimerFunc(30, timer, 0)


# Main function
glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(W, H)
glutCreateWindow(b"Traffic Signal Simulation")
glEnable(GL_DEPTH_TEST)
glClearColor(0.5, 0.6, 0.72, 1)
glutDisplayFunc(display)
glutKeyboardFunc(keyboard)
glutSpecialFunc(special)
glutMouseFunc(mouse)
glutMotionFunc(motion)
glutPassiveMotionFunc(passive)
glutTimerFunc(30, timer, 0)
glutMainLoop()