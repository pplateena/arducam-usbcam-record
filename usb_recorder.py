import cv2
import time
import os
from datetime import datetime

class USBRecorder:
    def __init__(self, camera_index=0, resolution=(1280, 720), fps=30):
        self.camera_index = camera_index
        self.resolution = resolution
        self.target_fps = fps
        self.camera = None
        self.is_recording = False
        
    def initialize_camera(self):
        self.camera = cv2.VideoCapture(self.camera_index)
        
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open USB camera at index {self.camera_index}")
        
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        self.camera.set(cv2.CAP_PROP_FPS, self.target_fps)
        
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
        
        print(f"USB camera initialized:")
        print(f"  Resolution: {actual_width}x{actual_height}")
        print(f"  FPS: {actual_fps}")
        
        return True
    
    def record_video(self, duration_seconds, output_path="recordings"):
        if not self.camera:
            raise RuntimeError("Camera not initialized. Call initialize_camera() first.")
        
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_path, f"usb_camera_{timestamp}.avi")
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        writer = None
        
        self.is_recording = True
        start_time = time.time()
        frame_count = 0
        
        print(f"Recording USB camera for {duration_seconds} seconds...")
        
        try:
            while self.is_recording and (time.time() - start_time) < duration_seconds:
                ret, frame = self.camera.read()
                
                if ret:
                    if writer is None:
                        height, width = frame.shape[:2]
                        writer = cv2.VideoWriter(filename, fourcc, self.target_fps, (width, height))
                    
                    writer.write(frame)
                    frame_count += 1
                    
                    cv2.imshow('USB Camera Recording', frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    print("Warning: Failed to read frame from USB camera")
                    time.sleep(0.01)
        
        finally:
            self.is_recording = False
            cv2.destroyAllWindows()
            if writer:
                writer.release()
        
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        
        print(f"USB camera recording completed:")
        print(f"  Duration: {elapsed_time:.2f} seconds")
        print(f"  Frames recorded: {frame_count}")
        print(f"  Average FPS: {fps:.2f}")
        print(f"  Video file: {filename}")
        
        return {
            "file": filename,
            "duration": elapsed_time,
            "frame_count": frame_count,
            "fps": fps
        }
    
    def stop_recording(self):
        self.is_recording = False
    
    def close(self):
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    recorder = USBRecorder()
    
    try:
        recorder.initialize_camera()
        result = recorder.record_video(10)  # Record for 10 seconds
        print("Recording result:", result)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        recorder.close()