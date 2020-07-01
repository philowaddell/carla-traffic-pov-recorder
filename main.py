#!/usr/bin/env python

import glob
import os
import sys

try:
    sys.path.append(glob.glob('../Carla_0.9.9_Compiled/PythonAPI/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


import carla

import random
import time

import _thread
import threading

import numpy as np
import cv2
from PIL import Image 
from Recorder import Recorder

 
def main():
    vehicle_list = []
    camera_list = []
    fps = 30
    resolution = (1280,720)
    number_of_vehicles = 10
    number_of_cameras = 2
    recording_duration = 15
    synchronous_mode = True
    parallel_recording = True
    
    print('\n|---------- Config ----------|')
    print('| FPS ................... %d |' % fps)
    print('| Resolution .... %d x %d |' % (resolution[0], resolution[1]))
    print('| Synchronous Mode .... %r |' % synchronous_mode)
    print('| Vehicle Count ......... %d |' % number_of_vehicles)
    print('| Camera Count ........... %d |' % number_of_cameras)
    print('| Parallel Recording .. %r |' % parallel_recording)
    print('| Recording Duration .... %d |' % recording_duration)
    print('|----------------------------|\n')
    
    
    try:
        ticks = 0
        # Create simulation and get world
        client = carla.Client('localhost', 2000, worker_threads=0)
        client.set_timeout(10.0)

        world = client.get_world()
        settings = world.get_settings()
        #settings.synchronous_mode = synchronous_mode # Enables synchronous mode
        settings.fixed_delta_seconds = 1/fps
        world.apply_settings(settings)

        # Retrive filtered blueprint library
        blueprint_library = world.get_blueprint_library()
        vehicle_blueprints = [x for x in blueprint_library.filter('Vehicle') if int(x.get_attribute('number_of_wheels')) == 4]

        #----------- Spawning Vehicles -----------#
        
        # Randomise spawn points
        spawn_points = world.get_map().get_spawn_points()
        random.shuffle(spawn_points)
        
        batch = []
        for n, transform in enumerate(spawn_points):
        
            if n >= number_of_vehicles:
                break
                
            #bp = random.choice(vehicle_blueprints)
            blueprint = blueprint_library.find('vehicle.audi.tt')
            
            if blueprint.has_attribute('color'):
                color = random.choice(blueprint.get_attribute('color').recommended_values)
                blueprint.set_attribute('color', color)
            blueprint.set_attribute('role_name', 'autopilot')
            
            vehicle = world.spawn_actor(blueprint, transform)
            #vehicle.set_autopilot(True, traffic_manager.get_port())
            vehicle_list.append(vehicle)
           
        print('INFO: Spawned %d vehicles' % number_of_vehicles)
        
        #----------- Setting up Traffic Manager -----------#
        
        # Setting up traffic manager
        print('INFO: Starting traffic manager..')
        traffic_manager = client.get_trafficmanager()
        tm_port = traffic_manager.get_port()
        
        for v in vehicle_list:
            v.set_autopilot(True, tm_port)
        print('INFO: Done.')
        
        # Swapping to asynchronous server
        print('INFO: Starting asynchronous mode..')
        settings.synchronous_mode = synchronous_mode # Enables synchronous mode
        world.apply_settings(settings)
        print('INFO: Done.')
        
        #----------- Recording -----------#
        
        for cam in range(number_of_cameras):
            camera_name = 'cam' + str(cam)
            camera = Recorder(world, camera_name, blueprint_library, fps, resolution)
            camera_list.append(camera)
            
        if parallel_recording:
            for camera in camera_list:
                target_vehicle = random.choice(vehicle_list)
                camera.attach(target_vehicle)
                
            while ticks <= recording_duration * fps:
                world.tick()
                ticks += 1
                time.sleep(1/fps)
            
            ticks = 0
                
            for camera in camera_list:
                camera.stop()
                
        # Sequential Recording        
        else:
            for camera in camera_list:
                target_vehicle = random.choice(vehicle_list)
                camera.attach(target_vehicle)
                
                while ticks <= recording_duration * fps:
                    world.tick()
                    ticks += 1
                    time.sleep(1/fps)
                    
                ticks = 0
                
                camera.stop()

        # Wait for rendering to finish
        while( any( [camera.is_recording() for camera in camera_list] ) ):
            world.tick()
            time.sleep(1/fps)
            
        #----------- End -----------#
        

    finally:
        print('INFO: Starting synchronous mode..')
        settings.synchronous_mode = False # Disables synchronous mode
        world.apply_settings(settings)
        print('INFO: Destroying actors..')
        client.apply_batch([carla.command.DestroyActor(x) for x in vehicle_list])
        print('INFO: Done.')


if __name__ == '__main__':

    main()
