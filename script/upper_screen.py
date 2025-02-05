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
import time
import argparse
import datetime
import contextlib

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
mn1.set_speed(1)
mn2 = MovingNode(pm.speed_unit)
mn2.setup(5, (255, 0, 0, 255), 'mn2')
mn1.set_speed(2)
for mn in [mn1, mn2]:
    moving_nodes_pool[mn.name] = mn
    mn.go()


# %% ---- 2025-02-05 ------------------------
# Function and class


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
        while self.running:
            # Draw the nodes in the pool.
            img = None
            for mn in moving_nodes_pool.values():
                if img:
                    # Update existing img.
                    img = pm.draw_node_at_distance(
                        mn.distance, mn.radius, mn.color, img)
                else:
                    # Create new img.
                    img = pm.draw_node_at_distance(
                        mn.distance, mn.radius, mn.color)

            # If the img is still None, use the random image.
            if not img:
                img = self._generate_random_image()

            with self.acquire_lock():
                self.pixmap = QPixmap.fromImage(ImageQt(img))
            time.sleep(0.01)


# %% ---- 2025-02-05 ------------------------
# Play ground
if __name__ == '__main__':
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
