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
    actor_list = []
    fps = 30
    resolution = (1280,720)
    number_of_vehicles = 10
    number_of_cameras = 1
    synchronous_mode = True
    
    print('\n|---------- Config ----------|')
    print('| FPS ................... %d |' % fps)
    print('| Resolution .... %d x %d |' % (resolution[0], resolution[1]))
    print('| Synchronous Mode .... %r |' % synchronous_mode)
    print('| Vehicle Count ......... %d |' % number_of_vehicles)
    print('| Camera Count ........... %d |' % number_of_cameras)
    print('|----------------------------|\n')
    
    
    try:
        ticks = 0
        # Create simulation and get world
        client = carla.Client('localhost', 2000, worker_threads=0)
        client.set_timeout(10.0)

        world = client.get_world()
        settings = world.get_settings()
        settings.synchronous_mode = synchronous_mode # Enables synchronous mode
        settings.fixed_delta_seconds = 1/fps
        world.apply_settings(settings)

        # Retrive filtered blueprint library
        blueprint_library = world.get_blueprint_library()
        vehicle_blueprints = [x for x in blueprint_library.filter('Vehicle') if int(x.get_attribute('number_of_wheels')) == 4]
        
        # Setting up Traffic Manager
        traffic_manager = client.get_trafficmanager(8000)

        # Set random spawn point
        #transform = random.choice(world.get_map().get_spawn_points())
        
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
            vehicle.set_autopilot(True, traffic_manager.get_port())
            vehicle_list.append(vehicle)
           
        print('INFO: Spawned %d vehicles' % number_of_vehicles)


        cam1 = Recorder(world, 'cam1', blueprint_library, fps, resolution)
        actor_list.append(cam1)
        
        cam2 = Recorder(world, 'cam2', blueprint_library, fps, resolution)
        actor_list.append(cam2)
        
        target_vehicle = random.choice(vehicle_list)
        cam1.attach(target_vehicle)
        
        target_vehicle = random.choice(vehicle_list)
        cam2.attach(target_vehicle)

        while ticks <= 500:
            world.tick()
            ticks += 1
            time.sleep(1/fps)
            
        cam1.stop() 
        cam2.stop() 
        ticks = 0
        
        while(cam1.is_recording() or cam2.is_recording() ):
            world.tick()
            time.sleep(1/fps)
        

    finally:

        print('INFO: Destroying actors..')
        cam1.destroy()
        client.apply_batch([carla.command.DestroyActor(x) for x in vehicle_list])
        settings.synchronous_mode = False # Disables synchronous mode
        world.apply_settings(settings)
        print('INFO: Done.')


if __name__ == '__main__':

    main()
