import glob
import os
import sys

try:
    sys.path.append(glob.glob('../../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import cv2
import threading
import time
from PIL import Image 
import numpy as np
import sys
sys.path.append(".")

class Recorder(object):
    def __init__(self, world, id, bp_lib, fps, res):
        self.world = world
        self.cam_id = id
        self.camera = None  # Carla camera
        self.fps = fps
        self.resolution = res
        self.filename = self.set_filename()
        self.bp = bp_lib.find('sensor.camera.rgb')
        self.frame_buffer = [] # List of frames for current recording
        self.video_buffer = [] # Queue of videos to be rendered
        self.set_res(res)
        
        # Thread for rendering in background
        thread = threading.Thread(target=self.renderer, args=())    
        thread.daemon = True  
        thread.start()
    
    # Attaches new camera to vehicle, sets it listening  
    def attach(self, vehicle):
       print('INFO: %s started recording..' % self.cam_id)
       # Positioning camera on bonnet (TODO: Make car specific)
       transform = carla.Transform(carla.Location(x=0.5, z=1.3)) 
       self.camera = self.world.spawn_actor(self.bp, transform, attach_to=vehicle)
       self.camera.listen(lambda carla_image: self.add(carla_image))    # Called every tick
    
    # Set resolution
    def set_res(self, res):
        self.resolution = res
        self.bp.set_attribute('image_size_x', str(res[0]))
        self.bp.set_attribute('image_size_y', str(res[1]))
        self.bp.set_attribute('fov', '110')
    
    # Add current tick frame to buffer
    def add(self, carla_image):
        self.frame_buffer.append(carla_image)
    
    # Stop recording
    def stop(self):
        print('INFO: %s stopped recording.' % self.cam_id)
        self.destroy()
        self.video_buffer.append(self.frame_buffer)
        self.frame_buffer = []
    
    # Video Renderer (TODO: Move to new threaded class)
    def renderer(self):
        while True:
            while len(self.video_buffer) == 0:
                time.sleep(5)
                
            frame_list = self.video_buffer[0]
            
            print('INFO: %s is exporting \'%s\' (%d frames)..' % (self.cam_id, self.filename, len(frame_list)))

            out = cv2.VideoWriter('_out/' + self.filename, cv2.VideoWriter_fourcc('D','I','V','X'), self.fps, self.resolution) 

            for i in range(len(frame_list)):
                data = frame_list[i].raw_data
                frame = np.array(Image.frombytes("RGBA", self.resolution, data.tobytes()))[:,:,0:3]
                out.write(frame)
                
            out.release()
            
            print('INFO: Saved \'%s\' successfully.' % self.filename)
            
            filenumber = str(int(self.filename[len(self.cam_id)+1:-4])+1).zfill(6)
            self.filename = self.cam_id + '_' + filenumber + '.avi'
            
            del self.video_buffer[0]
        
    def clear(self):
        self.fame_buffer = []
        
    def destroy(self):
        self.camera.destroy()
        
    def set_filename(self):
        if not os.path.exists('_out'):
            os.makedirs('_out')
         
        entries = os.listdir('_out/')
        
        if len(entries) != 0:
            max_filenumber = max(entries)[len(self.cam_id)+1:-4]
            filenumber = str(int(max_filenumber)+1).zfill(6)
        else:
            filenumber = str(0).zfill(6)
        
        return self.cam_id + '_' + filenumber + '.avi'
        
    def is_recording(self):
        if self.frame_buffer == [] and self.video_buffer == []:
            return False
        else:
            return True

        
        
        