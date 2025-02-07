"""
File: bomb.py
Author: Chuncheng Zhang
Date: 2025-02-07
Copyright & Email: chuncheng.zhang@ia.ac.cn

Purpose:
    The bomb animation.

Functions:
    1. Requirements and constants
    2. Function and class
    3. Play ground
    4. Pending
    5. Pending
"""


# %% ---- 2025-02-07 ------------------------
# Requirements and constants
from PIL import Image, ImageDraw
import time


# %% ---- 2025-02-07 ------------------------
# Function and class
class Bomb:
    position: tuple
    duration = 1.0  # seconds
    t0: float  # seconds, start time.
    t1: float  # seconds, stop time.
    r0: int = 10  # pixels, start radius.
    r1: int = 20  # pixels, stop radius.
    color = (255, 0, 0, 255)  # RGBA
    name: str = 'name of MovingNode'
    img_cache = None  # Cache for the new image
    draw_cache = None  # Cache for ImageDraw object

    def __init__(self, position, t0: float = None, duration: float = None, color=None, name: str = None):
        if not t0:
            t0 = time.time()
        self.t0 = t0
        if duration:
            self.duration = duration
        if color:
            self.color = color
        if name:
            self.name = name
        self.position = position
        self.t1 = self.t0 + self.duration

    def fetch_now(self, t: float = None):
        '''
        Fetch the current radius and progress.

        :param t: current time.

        :return: current radius and progress.
        '''
        if not t:
            t = time.time()
        # progress is in (0, 1)
        progress = 1-(t - self.t0)/self.duration
        # radius is between self.r0 and self.r1 with linear interpolation as progress.
        radius = self.r0 * progress + self.r1 * (1-progress)
        return radius, progress

    def check_if_expired(self, t: float = None):
        '''
        Check if the current time exceed the stop time.

        :param t: current time.

        :return: True if the current time exceed the stop time, otherwise False.
        '''
        if not t:
            t = time.time()
        return t > self.t1

    def draw(self, image: Image, t: float = None):
        # Method 1
        # Fast but ugly.
        draw = ImageDraw.Draw(image)
        radius, progress = self.fetch_now(t)
        x, y = self.position
        a = int(self.color[3] * progress)
        color = (self.color[0], self.color[1], self.color[2], a)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
        return image

    def draw_2(self, image: Image, t: float = None):
        # Method 2 (optimized for better performance)
        if self.img_cache is None or self.img_cache.size != image.size:
            self.img_cache = Image.new('RGBA', image.size, (0, 0, 0, 0))
            self.draw_cache = ImageDraw.Draw(self.img_cache)
        else:
            self.draw_cache.rectangle(
                [0, 0, self.img_cache.size[0], self.img_cache.size[1]], fill=(0, 0, 0, 0))

        radius, progress = self.fetch_now(t)
        x, y = self.position
        a = int(self.color[3] * progress)
        color = (self.color[0], self.color[1], self.color[2], a)

        self.draw_cache.ellipse(
            (x - radius, y - radius, x + radius, y + radius), fill=color)

        # Faster
        return Image.alpha_composite(image, self.img_cache)

        # Very slow
        return Image.composite(self.img_cache, image, self.img_cache)


# %% ---- 2025-02-07 ------------------------
# Play ground


# %% ---- 2025-02-07 ------------------------
# Pending


# %% ---- 2025-02-07 ------------------------
# Pending
