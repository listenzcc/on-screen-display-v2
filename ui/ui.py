"""
File: ui.py
Author: Chuncheng Zhang
Date: 2025-02-06
Copyright & Email: chuncheng.zhang@ia.ac.cn

Purpose:
    NiceGUI ui.

Functions:
    1. Requirements and constants
    2. Function and class
    3. Play ground
    4. Pending
    5. Pending
"""


# %% ---- 2025-02-06 ------------------------
# Requirements and constants
import sys
import json
import socket
import argparse
import numpy as np
from nicegui import ui
from omegaconf import OmegaConf

# Parse arguments and generate CONFIG
parser = argparse.ArgumentParser(description='UI with NiceGUI')
parser.add_argument('-c', '--config_file', type=str,
                    help='config file', required=True)
opt = parser.parse_args(sys.argv[1:])
CONFIG = OmegaConf.load(opt.config_file)

# %% ---- 2025-02-06 ------------------------
# Function and class
# The socket client interface communicating with upper_screen


class SocketClient:
    host = 'localhost'
    port = CONFIG.upperScreen.port

    def send_message(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            message = json.dumps(message).encode('utf-8')
            length = len(message).to_bytes(4, byteorder='big')
            s.sendall(length + message)
            response = b""
            length = int.from_bytes(s.recv(4), byteorder='big')
            while len(response) < length:
                packet = s.recv(4096)
                if not packet:
                    break
                response += packet
        return response.decode('utf-8')

    def list_nodes(self):
        return self.send_message({'command': 'list_nodes'})

    def update_node(self, name, speed, color):
        return self.send_message({
            'command': 'update_node',
            'name': name,
            'speed': speed,
            'color': color
        })

    def append_node(self):
        return self.send_message({
            'command': 'append_node'
        })

    def toggle_node_running_state(self, name: str, toggleToState: bool):
        return self.send_message({
            'command': 'toggle_node_running_state',
            'name': name,
            'toggleToState': toggleToState
        })

    def change_node_speed(self, name: str, speed: float):
        return self.send_message({
            'command': 'change_node_speed',
            'name': name,
            'speed': speed
        })

    def reset_node_distance(self, name: str):
        return self.send_message({
            'command': 'reset_node_distance',
            'name': name
        })

    def remove_node(self, name: str):
        return self.send_message({
            'command': 'remove_node',
            'name': name
        })

    def regenerate_map(self, checkpoints: list):
        return self.send_message({
            'command': 'regenerate_map',
            'checkpoints': checkpoints
        })


socket_client = SocketClient()


# ----------------------------------------
# ---- Related method ----

def append_node():
    ui.notify(json.loads(socket_client.append_node()))
    update_node_card()


def remove_node(name: str):
    ui.notify(json.loads(socket_client.remove_node(name)))
    update_node_card()


def regenerate_map(content):
    checkpoints = content['checkpoints']
    ui.notify(json.loads(socket_client.regenerate_map(checkpoints)))
    update_node_card()

# ----------------------------------------
# ---- Rows layout ----


class Rows:
    mapControl = ui.row()
    separator = ui.separator()
    addNode = ui.row()
    nodeCard = ui.row()


rows = Rows()


with rows.mapControl:
    row = ui.row()
    content = dict(n=7)

    def randomize_checkpoints():
        row.clear()
        content['checkpoints'] = np.random.random((content['n'], 2)).tolist()

        def change_checkpoints(e):
            content['checkpoints'] = e.content['json']['checkpoints']

        def reset_num_checkpoints(e):
            print(e)
            content['n'] = e.value

        with row:
            with ui.column():
                ui.button('Regenerate Map',
                          on_click=lambda e: regenerate_map(content),
                          color='red')
                ui.separator()
                ui.button('Randomize Checkpoints',
                          on_click=randomize_checkpoints)
                ui.slider(
                    min=4, max=20, value=content['n'], on_change=reset_num_checkpoints).props('label-always')
            ui.json_editor({'content': {'json': content}},
                           on_change=lambda e: change_checkpoints(e)).style('max-height: 24em; overflow: scroll')
    randomize_checkpoints()


with rows.addNode:
    ui.button('Append Node', on_click=append_node)


def mk_card_for_node(node):
    name = node['name']
    with ui.card().style('width: 300px'):
        # Put the circle icon with the node['color'] filled on the top right corner of the card.
        color = f"rgba({node['color'][0]}, {node['color'][1]}, {
            node['color'][2]}, {node['color'][3] / 255})"
        with ui.row().classes('w-full'):
            ui.space()
            ui.label(f"Name: {node['name']}").style('font-weight: bold;')
            ui.space()
            ui.icon('circle').style(f'color: {color}; font-size: 12px;')

        with ui.list().props('dense separator'):
            ui.item(f"Color: {node['color']}")
            ui.item(f"Radius: {node['radius']}")
            ui.item(f"Speed: {node['speed']:0.4f}")
            ui.item(f"Running: {node['running']}")
            ui.item(f"Distance: {node['distance']:0.4f}")

        ui.separator()
        ui.slider(min=0.1, max=10, value=node['speed']).props('label-always').on(
            'update:model-value',
            lambda e: socket_client.change_node_speed(name, e.args),
            leading_events=False)

        ui.switch(
            'Running', value=node['running'],
            on_change=lambda e: socket_client.toggle_node_running_state(name, e.value))

        with ui.row().classes('w-full'):
            ui.button('Restart',
                      on_click=lambda e: socket_client.reset_node_distance(name))
            ui.space()
            ui.button('Remove', color='red',
                      on_click=lambda e: remove_node(name))


def update_node_card():
    rows.nodeCard.clear()
    nodes = json.loads(socket_client.list_nodes())
    with rows.nodeCard:
        for node in nodes:
            mk_card_for_node(node)
    return


ui.timer(5.0, update_node_card)

# %% ---- 2025-02-06 ------------------------
# Play ground
if __name__ in {"__main__", "__mp_main__"}:
    ui.run()


# %% ---- 2025-02-06 ------------------------
# Pending


# %% ---- 2025-02-06 ------------------------
# Pending
