"""
File: upper_screen.py
Author: Chuncheng Zhang
Date: 2025-02-05
Copyright & Email: chuncheng.zhang@ia.ac.cn

Purpose:
    Upper screen display.

Functions:
    1. Requirements and constants
    2. Function and class
    3. Play ground
    4. Pending
    5. Pending
"""


# %% ---- 2025-02-05 ------------------------
# Requirements and constants
import sys
import json
import time
import random
import argparse
import datetime
import contextlib
import socketserver

from omegaconf import OmegaConf
from PIL.ImageQt import ImageQt
from PIL import Image, ImageDraw, ImageFont
from threading import Thread, RLock

from PyQt6.QtWidgets import QMainWindow, QApplication, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QTimer

from local_log import logger
from path_map import PathMap
from moving_node import MovingNode
from bomb import Bomb


# Parse arguments and generate CONFIG
parser = argparse.ArgumentParser(description='Upper screen display')
parser.add_argument('-c', '--config_file', type=str,
                    help='config file', required=True)
opt = parser.parse_args(sys.argv[1:])
CONFIG = OmegaConf.load(opt.config_file)

# Prepare
app = QApplication(sys.argv)
logger.debug(f'App: {app}')

screen = app.screens()[CONFIG.upperScreen.screenId]
logger.debug(
    f'Screen: {CONFIG.upperScreen.screenId}: {screen}, {screen.size()}')

# Instances
pm = PathMap()
pm.setup_road_randomly()
pm.generate_road_map_image(CONFIG.upperScreen.width, CONFIG.upperScreen.height)


# Moving nodes
moving_nodes_pool = dict()
mn1 = MovingNode(pm.speed_unit)
mn1.setup(5, (255, 255, 0, 255), 'mn1')
mn1.set_speed(1.3)
mn2 = MovingNode(pm.speed_unit)
mn2.setup(5, (255, 0, 0, 255), 'mn2')
mn2.set_speed(0.7)
for mn in [mn1, mn2]:
    moving_nodes_pool[mn.name] = mn
    mn.go()


# %% ---- 2025-02-05 ------------------------
# Function and class
class RunningBombsPool:
    pool = []
    num: int = 0

    @property
    def size(self):
        return len(self.pool)

    def append(self, bomb: Bomb):
        '''
        Append a bomb to the pool.

        :param bomb: the bomb to append.

        :return: the appended bomb.
        '''
        # Only append the bomb if it is a bomb.
        if isinstance(bomb, Bomb):
            self.pool.append(bomb)
            # logger.debug(f'Append bomb: {bomb}, {self.size}')
        return bomb

    def remove_expired_bombs(self):
        '''
        Remove expired bombs from the pool.

        :return: the size of the pool.
        '''
        n = self.size
        self.pool = [e for e in self.pool if not e.check_if_expired()]
        m = self.size
        # if m != n:
        #     logger.debug(f'Pool size changed {n} -> {m}')
        return m


# Bombs
rbp = RunningBombsPool()


def random_rgba_color():
    return tuple([random.randint(0, 256) for _ in range(3)] + [255])


class SocketServer:
    host = 'localhost'
    port = CONFIG.upperScreen.port
    encoding = 'utf-8'

    def ok_message(self, message: str = 'OK message'):
        return dict(status='OK', message=message)

    def failed_message(self, message: str = 'Failed message'):
        return dict(status='Failed', message=message)

    def simple_message(self, message):
        return json.dumps(message).encode(self.encoding)

    def send_with_length(self, handler_self, message):
        message = self.simple_message(message)
        length = len(message).to_bytes(4, byteorder='big')
        handler_self.request.sendall(length + message)

    def receive_with_length(self, handler_self):
        length = int.from_bytes(handler_self.request.recv(4), byteorder='big')
        data = b""
        while len(data) < length:
            packet = handler_self.request.recv(4096)
            if not packet:
                break
            data += packet
        return json.loads(data.decode(self.encoding))

    def start_socket_server(self):
        class RequestHandler(socketserver.BaseRequestHandler):
            def handle(handler_self):
                message = self.receive_with_length(handler_self)
                logger.debug(f"Received message: {message}")

                # List the nodes info.
                if message['command'] == 'list_nodes':
                    nodes_info = [
                        {
                            'name': node.name,
                            'color': node.color,
                            'radius': node.radius,
                            'speed': node.speed,
                            'running': node.running,
                            'distance': node.distance,
                            'displayBombThrowCircle': node.display_bomb_throw_circle,
                            'lambda': node.lamb
                        }
                        for node in moving_nodes_pool.values()
                    ]
                    self.send_with_length(handler_self, nodes_info)

                # Append new node.
                elif message['command'] == 'append_node':
                    # Find the available node name.
                    for i in range(1, 1000000):
                        name = f'mn{i}'
                        if name not in moving_nodes_pool:
                            break
                    # Append the node.
                    mn = MovingNode(pm.speed_unit)
                    mn.setup(5, random_rgba_color(), name)
                    s = random.uniform(0.5, 2.5)
                    s = float(f'{s:0.1f}')
                    mn.set_speed(s)
                    moving_nodes_pool[name] = mn
                    mn.go()
                    self.send_with_length(
                        handler_self, self.ok_message(f'Append {name}'))

                # Toggle the running state of the node.
                elif message['command'] == 'toggle_node_running_state':
                    def do(mn):
                        if message['toggleToState']:
                            mn.go()
                        else:
                            mn.stop()
                        return
                    if message.get('name') == '*':
                        for mn in moving_nodes_pool.values():
                            do(mn)
                    if mn := moving_nodes_pool.get(message.get('name')):
                        do(mn)
                    self.send_with_length(handler_self, self.ok_message())

                # Toggle the display state of the bomb throw circle
                elif message['command'] == 'toggle_node_display_bomb_throw_circle':
                    def do(mn):
                        mn.display_bomb_throw_circle = message['flag']
                    if message.get('name') == '*':
                        for mn in moving_nodes_pool.values():
                            do(mn)
                    if mn := moving_nodes_pool.get(message.get('name')):
                        do(mn)
                    self.send_with_length(handler_self, self.ok_message())

                # Change node speed.
                elif message['command'] == 'change_node_speed':
                    if mn := moving_nodes_pool.get(message.get('name')):
                        mn.set_speed(message['speed'])
                    self.send_with_length(handler_self, self.ok_message())

                # Change node lambda
                elif message['command'] == 'change_node_lambda':
                    def do(mn):
                        mn.set_lambda(message['lambda'])
                    if message.get('name') == '*':
                        for mn in moving_nodes_pool.values():
                            do(mn)
                    if mn := moving_nodes_pool.get(message.get('name')):
                        do(mn)
                    self.send_with_length(handler_self, self.ok_message())

                # Reset node distance to 0.
                elif message['command'] == 'reset_node_distance':
                    if mn := moving_nodes_pool.get(message.get('name')):
                        mn.reset_distance()
                    self.send_with_length(handler_self, self.ok_message())

                # Remove node.
                elif message['command'] == 'remove_node':
                    try:
                        moving_nodes_pool.pop(message.get('name'))
                    except KeyError:
                        pass
                    self.send_with_length(handler_self, self.ok_message())

                # Regenerate the map.
                elif message['command'] == 'regenerate_map':
                    # Set road randomly
                    # pm.setup_road_randomly()

                    # Set road from checkpoints
                    print(message['checkpoints'])
                    pm.setup_road(message['checkpoints'])

                    pm.generate_road_map_image(
                        CONFIG.upperScreen.width, CONFIG.upperScreen.height)

                    for mn in moving_nodes_pool.values():
                        mn.speed_unit = pm.speed_unit
                        mn.reset_distance()
                        logger.debug(f'Replace the node: {mn}')
                    self.send_with_length(handler_self, self.ok_message())

                # ! Add new handler here.
                elif message['command'] == 'update_node':
                    node_name = message['name']
                    if node_name in moving_nodes_pool:
                        node = moving_nodes_pool[node_name]
                        node.set_speed(message['speed'])
                        node.set_color(tuple(message['color']))
                        logger.debug(f"Updated node: {node_name}")
                    self.send_with_length(handler_self, self.ok_message())

                # Don't know what to do.
                else:
                    self.send_with_length(handler_self, self.ok_message())

        server = socketserver.TCPServer((self.host, self.port), RequestHandler)
        Thread(target=server.serve_forever, daemon=True).start()
        logger.info(f"Socket server started at {self.host}:{self.port}")


class DefaultImage:
    width = CONFIG.upperScreen.width
    height = CONFIG.upperScreen.height

    def _generate_random_image(self):
        '''
        Generate random RGBA image with self.width and self.height.
        The center of the image is the current time in HH:MM:SS.ms.

        :return: PIL.Image object.
        '''
        image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 100))
        draw = ImageDraw.Draw(image)
        current_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        font_size = 40  # Increased font size
        text_bbox = draw.textbbox(
            (0, 0), current_time, font=ImageFont.truetype("arial", font_size))
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        text_position = (
            (self.width - text_size[0]) // 2, (self.height - text_size[1]) // 2)
        draw.text(text_position, current_time, fill=(255, 255, 255,
                  200), font=ImageFont.truetype("arial", font_size))
        return image


class OnScreenPainter(DefaultImage):
    app = app
    screen = screen

    window = QMainWindow()
    pixmap_container = QLabel(window)
    pixmap = None

    _rlock = RLock()
    running = False
    key_pressed = ''

    t0 = 0
    frames = 0

    def __init__(self):
        super().__init__()
        self._prepare_window()
        logger.info('Initialized {}, {}'.format(
            self, {k: self.__getattribute__(k) for k in dir(self) if not k.startswith('_')}))

    def _prepare_window(self):
        # Translucent image by its RGBA A channel
        self.window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Disable frame and keep the window on the top layer.
        # It is necessary to set the FramelessWindowHint for the WA_TranslucentBackground works.
        # The WindowTransparentForInput option disables interaction.
        self.window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput
        )

        # Set the window size
        self.window.resize(self.width, self.height)

        # Put the window to the NW corner
        rect = self.screen.geometry()
        self.window.move(rect.x(), rect.y())

        # Set the pixmap_container accordingly,
        # and it is within the window bounds
        self.pixmap_container.setGeometry(0, 0, self.width, self.height)

    @contextlib.contextmanager
    def acquire_lock(self):
        self._rlock.acquire()
        try:
            yield
        finally:
            self._rlock.release()

    def repaint(self):
        with self.acquire_lock():
            if pixmap := self.pixmap:
                self.pixmap_container.setPixmap(pixmap)
        return

    def main_loop(self):
        if not self.running:
            Thread(target=self._main_loop, daemon=True).start()
        else:
            logger.error(
                'Failed to start main_loop, since it is already running.')

    def _main_loop(self):
        self.running = True
        self.t0 = time.time()
        t_report_interval = 10  # Seconds
        t_report = self.t0 + t_report_interval
        while self.running:
            # Report the frame rate at every t_report_gap seconds.
            self.frames += 1
            t = time.time()
            if t > t_report:
                t_report += t_report_interval
                logger.info(
                    f'Frame rate is {self.frames / (t - self.t0)}')

            # Init the empty img.
            img = None

            # Draw the nodes in the pool.
            rbp.remove_expired_bombs()
            for mn in list(moving_nodes_pool.values()):
                if img:
                    # Update existing img.
                    img = pm.draw_node_at_distance(mn, img)
                else:
                    # Create new img.
                    img = pm.draw_node_at_distance(mn)
                rbp.append(mn.throw_bomb())

            # Draw the bombs.
            if img:
                for bomb in rbp.pool:
                    img = bomb.draw(img)

            # If the img is still None, use the random image.
            if not img:
                img = self._generate_random_image()

            with self.acquire_lock():
                self.pixmap = QPixmap.fromImage(ImageQt(img))
            time.sleep(0.01)


# %% ---- 2025-02-05 ------------------------
# Play ground
if __name__ == '__main__':
    # Start server.
    ss = SocketServer()
    ss.start_socket_server()

    # Start on-screen painter.
    osp = OnScreenPainter()
    osp.window.show()
    osp.main_loop()

    def _on_every_timeout():
        osp.repaint()

    def _about_to_quit():
        '''
        Safely quit
        '''
        logger.debug('Safely quit the application')
        return

    # Bind the _about_to_quit and _on_key_pressed methods
    osp.app.aboutToQuit.connect(_about_to_quit)

    # Bind to the timer and run
    timer = QTimer()
    timer.timeout.connect(_on_every_timeout)
    timer.start()

    # Proper exit
    sys.exit(osp.app.exec())


# %% ---- 2025-02-05 ------------------------
# Pending


# %% ---- 2025-02-05 ------------------------
# Pending
