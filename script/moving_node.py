"""
File: moving_node.py
Author: Chuncheng Zhang
Date: 2025-02-05
Copyright & Email: chuncheng.zhang@ia.ac.cn

Purpose:
    The moving node in the path_map's PathMap.

Functions:
    1. Requirements and constants
    2. Function and class
    3. Play ground
    4. Pending
    5. Pending
"""


# %% ---- 2025-02-05 ------------------------
# Requirements and constants
import time
import numpy as np
import contextlib

from bomb import Bomb
from local_log import logger
from threading import Thread, RLock


# %% ---- 2025-02-05 ------------------------
# Function and class
class NodeAppearance:
    radius = 3  # pixels
    color = (255, 0, 0, 255)  # RGBA color
    name = 'Node1'  # node name, should be unique.
    display_bomb_throw_circle = True

    def setup(self, radius: float = None, color: tuple = None, name: str = None):
        if name:
            self.name = name
        if radius:
            self.radius = radius
        if color:
            self.color = color
        logger.info(
            f'Setup the node: name:{self.name}, radius:{self.radius}, color:{self.color}')

    def set_radius(self, radius: int):
        with self.lock():
            self.radius = radius
        logger.info(f'Node({self.name}) radius set to {self.radius}')

    def set_color(self, color: tuple):
        with self.lock():
            self.color = color
        logger.info(f'Node({self.name}) color set to {self.color}')


class BombThrower:
    bomb_throw_radius = 0.3  # radius for the bomb range.
    # the factor controlling how often the bomb is thrown.
    lamb = 3  # times per second
    # when the bomb is thrown
    t_throw: float = None  # seconds

    def set_lambda(self, lamb: float):
        with self.lock():
            self.lamb = lamb
        logger.info(f'Node({self.name}) lambda set to {self.lamb}')

    def compute_next_t_throw(self, t: float = None):
        '''
        Compute the next time the bomb is thrown.
        The dt follows the Poisson distribution with lambda = self.lamb.

        :param t: the current time.

        :return: the next time the bomb is thrown.
        '''
        if not t:
            t = time.time()
        u = np.random.uniform(1e-5, 1)
        dt = -1/self.lamb * np.log(u)
        self.t_throw = t + dt
        return self.t_throw

    def throw_bomb(self, t: float = None):
        '''
        Throw a bomb if it is ready, otherwise return None.

        :param t: the current time.

        :return: the bomb object if thrown, otherwise None.
        '''
        # No throws are allowed.
        if self.t_throw is None:
            return

        if not t:
            t = time.time()

        # The bomb is awaiting.
        if t < self.t_throw:
            return

        # Throw the bomb, and compute next throw time.
        # logger.debug(f'Throwing bomb at t={t}')
        self.t_throw = self.compute_next_t_throw(t)
        x, y, r = self._position
        u = np.random.uniform(0, 2*np.pi)
        r = np.random.uniform(0, r)
        position = (x + r * np.cos(u), y + r*np.sin(u))
        return Bomb(color=self.color, name=self.name, position=position)


class MovingNode(NodeAppearance, BombThrower):
    # Speed attributes
    speed = 1
    speed_limit = (0.1, 10)

    # Status
    running = False
    distance = 0.0

    # Where the node is plotted in.
    # It is changed only when the node is plotted.
    _position = None

    # RLock
    _rlock = RLock()

    def __init__(self, speed_unit: float):
        super().__init__()
        self.speed_unit = speed_unit
        logger.info(f'Initialized {self}')

    def go(self):
        '''Start the node moving.'''
        Thread(target=self._moving_loop, daemon=True).start()

    def stop(self):
        '''Stop the node from moving.'''
        self.running = False

    @contextlib.contextmanager
    def lock(self):
        self._rlock.acquire()
        try:
            yield
        finally:
            self._rlock.release()

    def reset_distance(self):
        self.distance = 0.0

    def _moving_loop(self):
        '''
        Start the moving loop.
        '''
        # Prevent repeat starting.
        if self.running:
            logger.error(f'Can not start moving, since it is already moving.')

        self.running = True
        self.compute_next_t_throw()
        try:
            # Init.
            t0 = time.time()
            logger.info(f'Node({self.name}) starts moving.')

            # Iteration.
            while self.running:
                time.sleep(0.01)
                with self.lock():
                    # Acquire dt and update self.t
                    t = time.time()
                    dt = t - t0
                    t0 = t
                    # Compute ds
                    ds = self.speed * self.speed_unit * dt
                    # Accumulate distance with ds
                    self.distance += ds
            logger.debug(f'Node({self.name}) stops running.')
        except Exception as e:
            # Something went wrong.
            import traceback
            traceback.print_exc()
            logger.error(f'Node({self.name}) stops moving with error {e}.')
            raise e
        finally:
            # Reset state.
            self.running = False
            logger.info(f'Node({self.name}) stops moving without error.')

    def set_speed(self, speed: float):
        with self.lock():
            self.speed = max(self.speed_limit[0], min(
                self.speed_limit[1], speed))
        logger.info(f'Node({self.name}) speed set to {self.speed}')


# %% ---- 2025-02-05 ------------------------
# Play ground


# %% ---- 2025-02-05 ------------------------
# Pending


# %% ---- 2025-02-05 ------------------------
# Pending
