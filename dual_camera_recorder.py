import cv2
import numpy as np
import ArducamDepthCamera as ac
import threading
import time
import os
from datetime import datetime

class DualCameraRecorder:
    def __init__(self, usb_camera_index=0, usb_resolution=(640, 480), usb_fps=30):
        self.usb_camera_index = usb_camera_index
        self.usb_resolution = usb_resolution
        self.usb_fps = usb_fps
        
        # Camera objects
        self.tof_camera = None
        self.usb_camera = None
        
        self.is_recording = False
        self.recording_threads = []
        self.results = {}
        
    def initialize_cameras(self):
        print("Initializing cameras...")
        
        # Initialize ToF camera
        try:
            print("Initializing ToF camera...")
            print("  SDK version:", ac.__version__)
            
            self.tof_camera = ac.ArducamCamera()
            ret = self.tof_camera.open(ac.Connection.CSI, 0)
            if ret != 0:
                raise RuntimeError(f"Failed to open ToF camera. Error code: {ret}")
            
            ret = self.tof_camera.start(ac.FrameType.RAW)
            if ret != 0:
                self.tof_camera.close()
                raise RuntimeError(f"Failed to start ToF camera. Error code: {ret}")
            
            print("ToF camera initialized successfully")
        except Exception as e:
            print(f"Failed to initialize ToF camera: {e}")
            raise
        
        # Initialize USB camera
        try:
            print("Initializing USB camera...")
            self.usb_camera = cv2.VideoCapture(self.usb_camera_index)
            
            if not self.usb_camera.isOpened():
                raise RuntimeError(f"Failed to open USB camera at index {self.usb_camera_index}")
            
            self.usb_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.usb_resolution[0])
            self.usb_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.usb_resolution[1])
            self.usb_camera.set(cv2.CAP_PROP_FPS, self.usb_fps)
            
            actual_width = int(self.usb_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.usb_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.usb_camera.get(cv2.CAP_PROP_FPS)
            
            print(f"USB camera initialized:")
            print(f"  Resolution: {actual_width}x{actual_height}")
            print(f"  FPS: {actual_fps}")
            
        except Exception as e:
            print(f"Failed to initialize USB camera: {e}")
            if self.tof_camera:
                self.tof_camera.stop()
                self.tof_camera.close()
            raise
        
        print("Both cameras initialized successfully")
        return True
    
    def _record_tof_thread(self, duration, output_path):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_path, f"tof_raw_{timestamp}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = None
            
            start_time = time.time()
            frame_count = 0
            
            print("ToF camera recording started...")
            
            while self.is_recording and (time.time() - start_time) < duration:
                frame = self.tof_camera.requestFrame(2000)
                if frame is not None and isinstance(frame, ac.RawData):
                    buf = frame.raw_data
                    self.tof_camera.releaseFrame(frame)
                    
                    # Convert to 8-bit format for saving
                    buf_8bit = (buf / (1 << 4)).astype(np.uint8)
                    
                    # Convert to color format for video saving
                    if len(buf_8bit.shape) == 2:
                        buf_colored = cv2.cvtColor(buf_8bit, cv2.COLOR_GRAY2BGR)
                    else:
                        buf_colored = buf_8bit
                    
                    # Initialize video writer with actual frame dimensions
                    if writer is None:
                        height, width = buf_colored.shape[:2]
                        writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
                    
                    writer.write(buf_colored)
                    frame_count += 1
            
            if writer:
                writer.release()
            
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            self.results['tof'] = {
                "file": filename,
                "duration": elapsed_time,
                "frame_count": frame_count,
                "fps": fps
            }
            
        except Exception as e:
            self.results['tof'] = {'error': str(e)}
            print(f"ToF recording error: {e}")
    
    def _record_usb_thread(self, duration, output_path):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_path, f"usb_camera_{timestamp}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = None
            
            start_time = time.time()
            frame_count = 0
            
            print("USB camera recording started...")
            
            while self.is_recording and (time.time() - start_time) < duration:
                ret, frame = self.usb_camera.read()
                
                if ret:
                    if writer is None:
                        height, width = frame.shape[:2]
                        writer = cv2.VideoWriter(filename, fourcc, self.usb_fps, (width, height))
                    
                    writer.write(frame)
                    frame_count += 1
                else:
                    time.sleep(0.01)
            
            if writer:
                writer.release()
            
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            self.results['usb'] = {
                "file": filename,
                "duration": elapsed_time,
                "frame_count": frame_count,
                "fps": fps
            }
            
        except Exception as e:
            self.results['usb'] = {'error': str(e)}
            print(f"USB recording error: {e}")
    
    def record_synchronized(self, duration_seconds, output_path="recordings"):
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        self.is_recording = True
        self.results = {}
        
        print(f"Starting synchronized recording for {duration_seconds} seconds...")
        print("Press Ctrl+C to stop recording early")
        
        tof_thread = threading.Thread(target=self._record_tof_thread, 
                                     args=(duration_seconds, output_path))
        usb_thread = threading.Thread(target=self._record_usb_thread, 
                                     args=(duration_seconds, output_path))
        
        self.recording_threads = [tof_thread, usb_thread]
        
        start_time = time.time()
        
        try:
            tof_thread.start()
            usb_thread.start()
            
            while self.is_recording and (time.time() - start_time) < duration_seconds:
                time.sleep(0.1)
                if not tof_thread.is_alive() and not usb_thread.is_alive():
                    break
            
        except KeyboardInterrupt:
            print("\nStopping recording...")
            self.stop_recording()
        
        tof_thread.join(timeout=5)
        usb_thread.join(timeout=5)
        
        self.is_recording = False
        
        elapsed_time = time.time() - start_time
        
        print(f"\nSynchronized recording completed in {elapsed_time:.2f} seconds")
        
        if 'tof' in self.results:
            if 'error' in self.results['tof']:
                print(f"ToF camera error: {self.results['tof']['error']}")
            else:
                print("ToF camera results:")
                print(f"  Video file: {self.results['tof']['file']}")
                print(f"  Frames: {self.results['tof']['frame_count']}")
                print(f"  FPS: {self.results['tof']['fps']:.2f}")
        
        if 'usb' in self.results:
            if 'error' in self.results['usb']:
                print(f"USB camera error: {self.results['usb']['error']}")
            else:
                print("USB camera results:")
                print(f"  Video file: {self.results['usb']['file']}")
                print(f"  Frames: {self.results['usb']['frame_count']}")
                print(f"  FPS: {self.results['usb']['fps']:.2f}")
        
        return self.results
    
    def stop_recording(self):
        self.is_recording = False
    
    def close(self):
        self.stop_recording()
        
        for thread in self.recording_threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        if self.tof_camera:
            self.tof_camera.stop()
            self.tof_camera.close()
        
        if self.usb_camera:
            self.usb_camera.release()
        
        cv2.destroyAllWindows()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Dual Camera Recorder - ToF and USB cameras')
    parser.add_argument('--duration', type=int, default=10, 
                       help='Recording duration in seconds (default: 10)')
    parser.add_argument('--output', type=str, default='recordings', 
                       help='Output directory (default: recordings)')
    parser.add_argument('--usb-camera', type=int, default=0, 
                       help='USB camera index (default: 0)')
    parser.add_argument('--usb-width', type=int, default=640, 
                       help='USB camera width (default: 640)')
    parser.add_argument('--usb-height', type=int, default=480, 
                       help='USB camera height (default: 480)')
    parser.add_argument('--usb-fps', type=int, default=30, 
                       help='USB camera FPS (default: 30)')
    
    args = parser.parse_args()
    
    recorder = DualCameraRecorder(
        usb_camera_index=args.usb_camera,
        usb_resolution=(args.usb_width, args.usb_height),
        usb_fps=args.usb_fps
    )
    
    try:
        recorder.initialize_cameras()
        results = recorder.record_synchronized(args.duration, args.output)
        
        print("\n" + "="*50)
        print("RECORDING SUMMARY")
        print("="*50)
        
        if results:
            for camera, result in results.items():
                print(f"\n{camera.upper()} Camera:")
                if 'error' in result:
                    print(f"  Status: ERROR - {result['error']}")
                else:
                    print(f"  Status: SUCCESS")
                    for key, value in result.items():
                        if key != 'error':
                            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        recorder.close()

if __name__ == "__main__":
    main()