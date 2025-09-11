import cv2
import numpy as np
import time
import os
from datetime import datetime
try:
    import ArducamDepthCamera as ac
except ImportError:
    print("ArducamDepthCamera not found. Please install the ArducamDepthCamera library.")
    ac = None

class ToFRecorder:
    def __init__(self, max_distance=4000):
        self.max_distance = max_distance
        self.camera = None
        self.is_recording = False
        
    def initialize_camera(self):
        if ac is None:
            raise ImportError("ArducamDepthCamera library not available")
            
        self.camera = ac.ArducamCamera()
        if self.camera.open(ac.TOFConnect.CSI, 0) != 0:
            if self.camera.open(ac.TOFConnect.USB, 0) != 0:
                raise RuntimeError("Failed to open Arducam ToF camera (tried both CSI and USB)")
        
        ret = self.camera.start(ac.TOFOutput.DEPTH)
        if ret != 0:
            raise RuntimeError("Failed to start Arducam ToF camera")
            
        return True
    
    def record_video(self, duration_seconds, output_path="recordings"):
        if not self.camera:
            raise RuntimeError("Camera not initialized. Call initialize_camera() first.")
        
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        depth_filename = os.path.join(output_path, f"tof_depth_{timestamp}.avi")
        amplitude_filename = os.path.join(output_path, f"tof_amplitude_{timestamp}.avi")
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        depth_writer = None
        amplitude_writer = None
        
        self.is_recording = True
        start_time = time.time()
        frame_count = 0
        
        print(f"Recording ToF camera for {duration_seconds} seconds...")
        
        try:
            while self.is_recording and (time.time() - start_time) < duration_seconds:
                frame = self.camera.requestFrame(200)
                if frame is not None:
                    depth_buf = frame.getDepthData()
                    amplitude_buf = frame.getAmplitudeData()
                    
                    depth_data = np.frombuffer(depth_buf, dtype=np.uint16, count=int(len(depth_buf)/2))
                    amplitude_data = np.frombuffer(amplitude_buf, dtype=np.uint16, count=int(len(amplitude_buf)/2))
                    
                    depth_data = depth_data.reshape((180, 240))
                    amplitude_data = amplitude_data.reshape((180, 240))
                    
                    depth_8bit = np.interp(depth_data, (0, self.max_distance), (0, 255)).astype(np.uint8)
                    amplitude_8bit = np.interp(amplitude_data, (0, 1024), (0, 255)).astype(np.uint8)
                    
                    depth_colored = cv2.applyColorMap(depth_8bit, cv2.COLORMAP_JET)
                    amplitude_colored = cv2.applyColorMap(amplitude_8bit, cv2.COLORMAP_GRAY)
                    
                    if depth_writer is None:
                        height, width = depth_colored.shape[:2]
                        depth_writer = cv2.VideoWriter(depth_filename, fourcc, 20.0, (width, height))
                        amplitude_writer = cv2.VideoWriter(amplitude_filename, fourcc, 20.0, (width, height))
                    
                    depth_writer.write(depth_colored)
                    amplitude_writer.write(amplitude_colored)
                    
                    frame_count += 1
                    self.camera.releaseFrame(frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        finally:
            self.is_recording = False
            if depth_writer:
                depth_writer.release()
            if amplitude_writer:
                amplitude_writer.release()
        
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        
        print(f"ToF recording completed:")
        print(f"  Duration: {elapsed_time:.2f} seconds")
        print(f"  Frames recorded: {frame_count}")
        print(f"  Average FPS: {fps:.2f}")
        print(f"  Depth video: {depth_filename}")
        print(f"  Amplitude video: {amplitude_filename}")
        
        return {
            "depth_file": depth_filename,
            "amplitude_file": amplitude_filename,
            "duration": elapsed_time,
            "frame_count": frame_count,
            "fps": fps
        }
    
    def stop_recording(self):
        self.is_recording = False
    
    def close(self):
        if self.camera:
            self.camera.stop()
            self.camera.close()

if __name__ == "__main__":
    recorder = ToFRecorder()
    
    try:
        recorder.initialize_camera()
        result = recorder.record_video(10)  # Record for 10 seconds
        print("Recording result:", result)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        recorder.close()