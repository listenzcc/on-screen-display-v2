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
import contextlib

from local_log import logger
from threading import Thread, RLock


# %% ---- 2025-02-05 ------------------------
# Function and class
class NodeAppearance(object):
    radius = 3
    color = (255, 0, 0, 255)
    name = 'Node1'

    def setup(self, radius: float = None, color: tuple = None, name: str = None):
        if name:
            self.name = name
        if radius:
            self.radius = radius
        if color:
            self.color = color
        logger.info(
            f'Setup the node: name:{self.name}, radius:{self.radius}, color:{self.color}')


class MovingNode(NodeAppearance):
    # Speed attributes
    speed = 1
    speed_limit = (0.1, 10)

    # Status
    running = False
    distance = 0.0

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

    def _moving_loop(self):
        '''
        Start the moving loop.
        '''
        # Prevent repeat starting.
        if self.running:
            logger.error(f'Can not start moving, since it is already moving.')

        self.running = True
        try:
            # Init.
            t0 = time.time()
            self.distance = 0.0
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

    def set_radius(self, radius: int):
        with self.lock():
            self.radius = radius
        logger.info(f'Node({self.name}) radius set to {self.radius}')

    def set_color(self, color: tuple):
        with self.lock():
            self.color = color
        logger.info(f'Node({self.name}) color set to {self.color}')


# %% ---- 2025-02-05 ------------------------
# Play ground


# %% ---- 2025-02-05 ------------------------
# Pending


# %% ---- 2025-02-05 ------------------------
# Pending
