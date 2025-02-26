"""
File: path_map.py
Author: Chuncheng Zhang
Date: 2025-02-05
Copyright & Email: chuncheng.zhang@ia.ac.cn

Purpose:
    The map with path.

Functions:
    1. Requirements and constants
    2. Function and class
    3. Play ground
    4. Pending
    5. Pending
"""


# %% ---- 2025-02-05 ------------------------
# Requirements and constants
import bezier
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from local_log import logger
from PIL import Image, ImageDraw, ImageOps
from moving_node import MovingNode

# %%
# Make the plane icon image, the black background is transparent.
plane_icon = Image.open(
    './img/plane-icon.png').resize((50, 50)).convert('RGBA')
# mask = ImageOps.invert(plane_icon.convert('L'))
mask = plane_icon.convert('L')
plane_icon.putalpha(mask)

# %% ---- 2025-02-05 ------------------------
# Function and class


def random_check_points(n: int):
    '''
    Create the random check points.

    :param n: the number of check points.
    :return: the check points.
    '''
    check_points = np.random.random((n, 2)) * 0.8 + 0.1
    return check_points


def extend_check_points(check_points: np.ndarray, length_threshold: float = 0.3, tail_length: float = 0.1):
    '''
    Extend the check points with the threshold.

    :param check_points: the check points.
    :param threshold: the threshold to extend.
    :return: the extended check points.
    '''
    n = len(check_points)
    extended_check_points = []
    for i in range(n-1):
        p1 = check_points[i]
        p2 = check_points[i+1]
        length = np.linalg.norm(p1 - p2)
        if length > length_threshold:
            r = tail_length / length
            extended_check_points.append(p1)
            extended_check_points.append(p1*(1-r) + p2*r)
            extended_check_points.append(p2*(1-r) + p1*r)
        else:
            extended_check_points.append(p1)
    extended_check_points.append(p2)
    return np.array(extended_check_points)


def mk_curve(check_points: np.ndarray):
    '''
    Create the bezier curve from a list of points.

    :param check_points: list of points.
    :return: the list of bezier curves.
    '''
    n = len(check_points)
    control_points = {}
    control_points[0] = dict(
        left=check_points[0], right=check_points[0]*0.5 + check_points[1]*0.5)
    control_points[n-1] = dict(
        left=check_points[-1]*0.5 + check_points[-2]*0.5, right=check_points[-1])
    for i in range(1, n-1):
        a = check_points[i-1]
        b = check_points[i]
        c = check_points[i+1]
        length = np.linalg.norm(a-c)
        control_points[i] = dict(
            left=b+(a-c)*0.05/length,
            right=b-(a-c)*0.05/length
        )
    curves = []
    for i in range(1, n):
        a = check_points[i-1]
        b = check_points[i]
        c = control_points[i-1]['right']
        d = control_points[i]['left']
        cp = np.array((a, c, d, b))
        curves.append(bezier.Curve.from_nodes(cp.T))
    return curves


class PathMap:
    schedule_time_cost: float = 10  # 10 * 60  # Seconds
    fps_in_schedule: float = 100  # fps
    total_points: int  # points as schedule_time_cost x fps_in_schedule points

    def __init__(self, schedule_time_cost: float = None, fps_in_schedule: int = None):
        '''
        Initialize the PathMap.

        :param schedule_time_cost: the new schedule_time_cost.
        :param fps_in_schedule: the new fps_in_schedule.
        '''
        self.reset_total_points(schedule_time_cost, fps_in_schedule)
        logger.info(f'Generated PathMap: {self}')

    def reset_total_points(self, schedule_time_cost: float = None, fps_in_schedule: int = None):
        '''
        Reset the total_points.

        :param schedule_time_cost: the new schedule_time_cost.
        :param fps_in_schedule: the new fps_in_schedule.
        '''
        if schedule_time_cost is not None:
            self.schedule_time_cost = schedule_time_cost
        if fps_in_schedule is not None:
            self.fps_in_schedule = fps_in_schedule
        self.total_points = int(self.schedule_time_cost * self.fps_in_schedule)
        logger.info(
            f'Reset schedule: {self.schedule_time_cost}, {self.fps_in_schedule}, {self.total_points}')

    def setup_road_randomly(self, n: int = 5):
        '''
        Setup the road with randomized check_points.

        1. cp = random_check_points(n)
        2. self.setup_road(cp)

        :param n: number of check_points.

        :return: the output of self.setup_road().
        '''
        check_points = random_check_points(n)
        return self.setup_road(check_points)

    def setup_road(self, check_points: np.ndarray):
        '''
        Setup the road with check_points.

        It generates the following attributes:
            self.speed_unit = speed_unit
            self.total_curve_length = total_curve_length
            self.large_table = large_table
            self.check_points = check_points
            self.curves = curves
            self.segment_table = segment_table

        :param n: number of points.

        :return segment_table: the dataframe with columns (idx, start, end, curve_length, curve_obj).
        :return large_table: the dataframe with columns (_s, segment, distance, pos, progress, schedule_time)
        '''
        # Generate check_points and curves.
        check_points = np.array(check_points)
        check_points = extend_check_points(check_points)
        curves = mk_curve(check_points)

        # Calculate the time cost and length of each curve.
        # Generate segment_table: (idx, start, end, curve_length, curve_obj)
        segment_table = []
        for i, curve in enumerate(curves):
            p1 = check_points[i]
            p2 = check_points[i+1]
            length = curve.length
            segment_table.append((i, p1, p2, length, curve))
        segment_table = pd.DataFrame(
            segment_table, columns=['idx', 'start', 'end', 'length', 'curve'])

        # Create the large_table.
        # It is the very detail table of the path at fine distance segments.
        # 1. Compute constants.
        total_curve_length = segment_table['length'].sum()
        speed_unit = total_curve_length / self.schedule_time_cost
        segment_table['n'] = (segment_table['length'] / total_curve_length *
                              self.total_points).map(int)
        segment_table['distance_offset'] = np.cumsum(
            segment_table['length']) - segment_table['length']

        # 2. Make the large table.
        large_table = []
        for i, slice in segment_table.iterrows():
            s = np.linspace(0, 1, slice['n'], endpoint=False)
            distance = np.linspace(slice['distance_offset'],
                                   slice['distance_offset'] + slice['length'], slice['n'])
            df = pd.DataFrame(s, columns=['_s'])
            df['segment'] = i
            df['distance'] = distance
            df['pos'] = df['_s'].map(
                lambda s: slice['curve'].evaluate(s).squeeze())
            large_table.append(df)
        large_table = pd.concat(large_table)
        n = len(large_table)
        large_table['progress'] = np.linspace(0, 1, n)
        large_table['schedule_time'] = np.linspace(
            0, self.schedule_time_cost, n)
        large_table.index = range(n)

        # Instance data
        self.speed_unit = speed_unit
        self.total_curve_length = total_curve_length
        self.large_table = large_table
        self.check_points = check_points
        self.curves = curves
        self.segment_table = segment_table
        return segment_table, large_table

    def plot_with_matplotlib(self):
        '''
        the trace is linear interpolated between the check points.
        plot the trace and mark the time between checkpoints.
        '''
        if self.check_points is None:
            print("No check points to plot.")
            return

        fig, ax = plt.subplots()

        # Plot check points
        ax.scatter(self.check_points[:, 0],
                   self.check_points[:, 1], c='r', marker='o')

        for curve in self.curves:
            curve.plot(num_pts=1000, ax=ax)

        # Plot linear interpolated trace with arrows and color based on time cost
        for i in range(len(self.check_points) - 1):
            p1 = self.check_points[i]
            p2 = self.check_points[i + 1]
            ax.annotate('', xy=(p2[0], p2[1]), xytext=(p1[0], p1[1]),
                        arrowprops=dict(arrowstyle="->", color='gray'))
            ax.text(x=p1[0], y=p1[1], s=f'{i}')
        ax.text(x=p2[0], y=p2[1], s=f'{i+1}')

        return fig

    def generate_road_map_image(self, width: int, height: int, padding: int = 0, alpha: int = 0):
        '''
        Generate the image with the given width, height and padding.
        The image content is the road map.

        :param width: width of the image.
        :param height: height of the image.
        :param padding: padding of the image.
        :param alpha: opacity of the image.

        :return: the PIL.Image object.
        '''
        # 1. Generate the PIL.Image as the size of (width + 2*padding, height + 2*padding), the mode is RGBA.
        image = Image.new('RGBA',
                          (width + 2 * padding, height + 2 * padding), (255, 255, 255, alpha))
        draw = ImageDraw.Draw(image)

        # 2. Draw the curves from the large_table's pos using a colormap
        colormap = plt.colormaps.get_cmap('viridis')
        for i, curve in enumerate(self.curves):
            color = tuple(int(c * 255)
                          for c in colormap(i/len(self.curves))[:3]) + (255,)
            points = curve.evaluate_multi(np.linspace(0, 1, 1000)).T
            scaled_points = [(x * width + padding, y * height + padding)
                             for x, y in points]
            draw.line(scaled_points, fill=color, width=2)

        # Draw the linear interpolation between check points
        for i in range(len(self.check_points) - 1):
            p1 = self.check_points[i]
            p2 = self.check_points[i + 1]
            x1, y1 = p1[0] * width + padding, p1[1] * height + padding
            x2, y2 = p2[0] * width + padding, p2[1] * height + padding
            draw.line([(x1, y1), (x2, y2)], fill=(128, 128, 128, 255), width=1)

        # 3. Return the image
        self.road_map_image = image
        self.road_map_image_draw = ImageDraw.Draw(image)
        self.padding = padding
        self.width = width
        self.height = height
        return image

    def draw_node_at_distance(self, mn: MovingNode, image: Image = None):
        '''
        Draw the node at the given distance, radius and color.

        :param mn: the moving node object.
        :param image: the image to draw, if None use self.road_map_image.copy() instead.

        :return: the updated image.
        '''
        # Prepare the image and draw obj.
        if image is None:
            image = self.road_map_image.copy()
        image_size_min = min(image.size)
        draw = ImageDraw.Draw(image)

        # Parse the information from the mn
        with mn.lock():
            # Prevent the distance from exceeding the total_curve_length.
            distance = mn.distance % self.total_curve_length
            radius = mn.radius
            color = mn.color
            bomb_throw_radius = mn.bomb_throw_radius
            _n = mn.distance_queue.qsize()
            distance_array = [mn.distance_queue.get() % self.total_curve_length
                              for i in range(_n-1)] + [distance]

        # Convert bomb_throw_radius into pixels
        bomb_throw_radius *= image_size_min

        # Acquire the slice with the largest distance less than the given distance.
        # If failed, return the first slice.
        try:
            slice = self.large_table[
                self.large_table['distance'].lt(distance)].iloc[-1]
        except:
            slice = self.large_table.iloc[0]
        x = slice['pos'][0] * self.width + self.padding
        y = slice['pos'][1] * self.height + self.padding
        # node body, draw the ellipse at the position.
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius), fill=color)

        # Draw the has-been-traveled road and the aircraft.
        try:
            d1 = distance_array[0]
            d2 = distance_array[-1]
            slice1 = self.large_table.query(f'distance<{d1}').iloc[-1]
            slice2 = self.large_table.query(f'distance<{d2}').iloc[-1]
            a = slice1.name
            b = slice2.name
            if a == b:
                a -= 1
            for i in range(a-1, b-1):
                x1 = self.large_table.loc[i,
                                          'pos'][0] * self.width + self.padding
                y1 = self.large_table.loc[i,
                                          'pos'][1] * self.height + self.padding

                x2 = self.large_table.loc[i+1,
                                          'pos'][0] * self.width + self.padding
                y2 = self.large_table.loc[i+1,
                                          'pos'][1] * self.height + self.padding

                self.road_map_image_draw.line(
                    [(x1, y1), (x2, y2)], fill=color, width=5)

            psi = np.arctan2(x2-x1, y2-y1)
            if mn.name == 'mn2':
                print(psi, x2-x1, y2-y1, a, b)
            icon = plane_icon.rotate(180+psi/np.pi*180)
            image.paste(
                icon, (int(x-icon.size[0]/2), int(y-icon.size[1]/2)), icon)
        except Exception:
            pass

        # bomb range, draw the ellipse at the position.
        if mn.display_bomb_throw_circle:
            draw.ellipse(
                (x - bomb_throw_radius, y - bomb_throw_radius,
                 x + bomb_throw_radius, y + bomb_throw_radius),
                outline=color)

        mn._position = (x, y, bomb_throw_radius)

        return image


# %% ---- 2025-02-05 ------------------------
# Play ground
if __name__ == '__main__':
    pm = PathMap()
    pm.setup_road_randomly()
    print(pm.segment_table)
    print(pm.large_table)
    pm.plot_with_matplotlib()
    plt.plot()
    plt.show()


# %% ---- 2025-02-05 ------------------------
# Pending


# %% ---- 2025-02-05 ------------------------
# Pending
