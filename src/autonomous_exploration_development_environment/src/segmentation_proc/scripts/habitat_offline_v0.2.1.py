#!/usr/bin/python3

import argparse

import math
import multiprocessing
import os
import random
import time
from enum import Enum

import numpy as np
from PIL import Image

import habitat_sim
import habitat_sim.agent
from habitat_sim.utils.common import (
    d3_40_colors_rgb,
    quat_from_coeffs,
)

from scipy.spatial.transform import Rotation as R

default_sim_settings = {
    "width": 640, # horizontal resolution
    "height": 360, # vertical resolution
    "hfov": 114.591560981, # horizontal FOV
    "camera_offset_z": 0, # camera z-offset
    "color_sensor": True,  # RGB sensor
    "depth_sensor": True,  # depth sensor
    "semantic_sensor": True,  # semantic sensor
    "scene": "../../vehicle_simulator/mesh/matterport/segmentations/matterport.glb",
    "trajectory": "../../vehicle_simulator/log/trajectory.txt",
    "save_dir": "./",
}

parser = argparse.ArgumentParser()
parser.add_argument("--scene", type=str, default=default_sim_settings["scene"])
parser.add_argument("--trajectory", type=str, default=default_sim_settings["trajectory"])
parser.add_argument("--save_dir", type=str, default=default_sim_settings["save_dir"])
args = parser.parse_args()

def make_settings():
    settings = default_sim_settings.copy()
    settings["scene"] = args.scene
    settings["trajectory"] = args.trajectory
    settings["save_dir"] = args.save_dir

    return settings

settings = make_settings()

def make_cfg(settings):
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.frustum_culling = True
    sim_cfg.gpu_device_id = 0
    if not hasattr(sim_cfg, "scene_id"):
        raise RuntimeError(
            "Error: Please upgrade habitat-sim. SimulatorConfig API version mismatch"
        )
    sim_cfg.scene_id = settings["scene"]

    sensor_specs = []
    def create_camera_spec(**kw_args):
        camera_sensor_spec = habitat_sim.CameraSensorSpec()
        camera_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
        camera_sensor_spec.resolution = [settings["height"], settings["width"]]
        camera_sensor_spec.position = [0, 0, 0]
        for k in kw_args:
            setattr(camera_sensor_spec, k, kw_args[k])
        return camera_sensor_spec

    if settings["color_sensor"]:
        color_sensor_spec = create_camera_spec(
            uuid="color_sensor",
            hfov=settings["hfov"],
            sensor_type=habitat_sim.SensorType.COLOR,
            sensor_subtype=habitat_sim.SensorSubType.PINHOLE,
        )
        sensor_specs.append(color_sensor_spec)

    if settings["depth_sensor"]:
        depth_sensor_spec = create_camera_spec(
            uuid="depth_sensor",
            hfov=settings["hfov"],
            sensor_type=habitat_sim.SensorType.DEPTH,
            channels=1,
            sensor_subtype=habitat_sim.SensorSubType.PINHOLE,
        )
        sensor_specs.append(depth_sensor_spec)

    if settings["semantic_sensor"]:
        semantic_sensor_spec = create_camera_spec(
            uuid="semantic_sensor",
            hfov=settings["hfov"],
            sensor_type=habitat_sim.SensorType.SEMANTIC,
            channels=1,
            sensor_subtype=habitat_sim.SensorSubType.PINHOLE,
        )
        sensor_specs.append(semantic_sensor_spec)

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = sensor_specs

    return habitat_sim.Configuration(sim_cfg, [agent_cfg])

class DemoRunnerType(Enum):
    BENCHMARK = 1
    EXAMPLE = 2
    AB_TEST = 3

class ABTestGroup(Enum):
    CONTROL = 1
    TEST = 2

class DemoRunner:
    def __init__(self, sim_settings, simulator_demo_type):
        if simulator_demo_type == DemoRunnerType.EXAMPLE:
            self.set_sim_settings(sim_settings)
        self._demo_type = simulator_demo_type

    def set_sim_settings(self, sim_settings):
        self._sim_settings = sim_settings.copy()

    def save_color_observation(self, obs, total_frames, save_dir):
        color_obs = obs["color_sensor"]
        color_img = Image.fromarray(color_obs, mode="RGBA")
        color_img.save(save_dir + "/rgb_%05d.png" % total_frames)

    def save_semantic_observation(self, obs, total_frames, save_dir):
        semantic_obs = obs["semantic_sensor"]
        semantic_img = Image.new("P", (semantic_obs.shape[1], semantic_obs.shape[0]))
        semantic_img.putpalette(d3_40_colors_rgb.flatten())
        semantic_img.putdata((semantic_obs.flatten() % 40).astype(np.uint8))
        semantic_img.save(save_dir + "/semantic_%05d.png" % total_frames)

    def save_depth_observation(self, obs, total_frames, save_dir):
        depth_obs = obs["depth_sensor"]
        depth_img = Image.fromarray((depth_obs / 10 * 255).astype(np.uint8), mode="L")
        depth_img.save(save_dir + "/depth_%05d.png" % total_frames)

    def init_common(self):
        self._cfg = make_cfg(self._sim_settings)
        scene_file = self._sim_settings["scene"]

        self._sim = habitat_sim.Simulator(self._cfg)

        if not self._sim.pathfinder.is_loaded:
            navmesh_settings = habitat_sim.NavMeshSettings()
            navmesh_settings.set_defaults()
            self._sim.recompute_navmesh(self._sim.pathfinder, navmesh_settings)

    def proc_trajectory(self, trajectory, save_dir):
        start_state = self.init_common()

        path_log = np.loadtxt(trajectory)
        path_log_len = len(path_log)
     
        total_sim_step_time = 0.0
        total_frames = 0
        start_time = time.time()

        while (total_frames < path_log_len):
            if total_frames == 1:
                start_time = time.time()

            position, roll, pitch, yaw = path_log[total_frames][:3], path_log[total_frames][3], path_log[total_frames][4], path_log[total_frames][5]

            roll = -roll
            yaw = 1.5708 - yaw

            qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
            qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
            qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
            qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)

            position[1], position[2] = position[2], -position[1]
            
            agent_state = self._sim.get_agent(0).get_state()
            for sensor in agent_state.sensor_states:
                agent_state.sensor_states[sensor].position = position + np.array([0, default_sim_settings["camera_offset_z"], 0])
                agent_state.sensor_states[sensor].rotation = quat_from_coeffs(np.array([-qy, -qz, qx, qw]))

            self._sim.get_agent(0).set_state(agent_state, infer_sensor_states = False)                
            observations = self._sim.step("move_forward")
            total_sim_step_time += self._sim._previous_step_time

            if self._sim_settings["color_sensor"]:
                self.save_color_observation(observations, total_frames, save_dir)
            if self._sim_settings["depth_sensor"]:
                self.save_depth_observation(observations, total_frames, save_dir)
            if self._sim_settings["semantic_sensor"]:
                self.save_semantic_observation(observations, total_frames, save_dir)

            state = self._sim.last_state()
            print("Frame: " + str(total_frames))
            total_frames += 1

        end_time = time.time()
        perf = {}
        perf["total_time"] = end_time - start_time
        perf["frame_time"] = perf["total_time"] / total_frames
        perf["fps"] = 1.0 / perf["frame_time"]
        perf["avg_sim_step_time"] = total_sim_step_time / total_frames

        self._sim.close()
        del self._sim

        return perf

demo_runner = DemoRunner(settings, DemoRunnerType.EXAMPLE)
perf = demo_runner.proc_trajectory(args.trajectory, args.save_dir)

print(" ========================= Performance ======================== ")
print(
    " %d x %d, total time %0.2f s,"
    % (settings["width"], settings["height"], perf["total_time"]),
    "frame time %0.3f ms (%0.1f FPS)" % (perf["frame_time"] * 1000.0, perf["fps"]),
)
print(" ============================================================== ")
