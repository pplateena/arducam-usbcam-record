import threading
import time
import os
from datetime import datetime
from tof_recorder import ToFRecorder
from usb_recorder import USBRecorder

class DualCameraRecorder:
    def __init__(self, usb_camera_index=0, max_distance=4000, 
                 usb_resolution=(1280, 720), usb_fps=30):
        self.tof_recorder = ToFRecorder(max_distance=max_distance)
        self.usb_recorder = USBRecorder(camera_index=usb_camera_index, 
                                       resolution=usb_resolution, 
                                       fps=usb_fps)
        
        self.is_recording = False
        self.recording_threads = []
        self.results = {}
        
    def initialize_cameras(self):
        print("Initializing cameras...")
        
        try:
            print("Initializing ToF camera...")
            self.tof_recorder.initialize_camera()
            print("ToF camera initialized successfully")
        except Exception as e:
            print(f"Failed to initialize ToF camera: {e}")
            raise
        
        try:
            print("Initializing USB camera...")
            self.usb_recorder.initialize_camera()
            print("USB camera initialized successfully")
        except Exception as e:
            print(f"Failed to initialize USB camera: {e}")
            self.tof_recorder.close()
            raise
        
        print("Both cameras initialized successfully")
        return True
    
    def _record_tof_thread(self, duration, output_path):
        try:
            self.results['tof'] = self.tof_recorder.record_video(duration, output_path)
        except Exception as e:
            self.results['tof'] = {'error': str(e)}
            print(f"ToF recording error: {e}")
    
    def _record_usb_thread(self, duration, output_path):
        try:
            self.results['usb'] = self.usb_recorder.record_video(duration, output_path)
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
                print(f"  Depth video: {self.results['tof']['depth_file']}")
                print(f"  Amplitude video: {self.results['tof']['amplitude_file']}")
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
        self.tof_recorder.stop_recording()
        self.usb_recorder.stop_recording()
    
    def close(self):
        self.stop_recording()
        
        for thread in self.recording_threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        self.tof_recorder.close()
        self.usb_recorder.close()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Dual Camera Recorder - ToF and USB cameras')
    parser.add_argument('--duration', type=int, default=10, 
                       help='Recording duration in seconds (default: 10)')
    parser.add_argument('--output', type=str, default='recordings', 
                       help='Output directory (default: recordings)')
    parser.add_argument('--usb-camera', type=int, default=0, 
                       help='USB camera index (default: 0)')
    parser.add_argument('--max-distance', type=int, default=4000, 
                       help='ToF camera max distance in mm (default: 4000)')
    parser.add_argument('--usb-width', type=int, default=1280, 
                       help='USB camera width (default: 1280)')
    parser.add_argument('--usb-height', type=int, default=720, 
                       help='USB camera height (default: 720)')
    parser.add_argument('--usb-fps', type=int, default=30, 
                       help='USB camera FPS (default: 30)')
    
    args = parser.parse_args()
    
    recorder = DualCameraRecorder(
        usb_camera_index=args.usb_camera,
        max_distance=args.max_distance,
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