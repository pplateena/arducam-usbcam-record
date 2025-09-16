import cv2
import numpy as np
import ArducamDepthCamera as ac
import time
import os
from datetime import datetime

class SyncFrameRecorder:
    def __init__(self, usb_camera_index=0, usb_resolution=(640, 480), usb_fps=30):
        self.usb_camera_index = usb_camera_index
        self.usb_resolution = usb_resolution
        self.usb_fps = usb_fps
        
        # Camera objects
        self.tof_camera = None
        self.usb_camera = None
        
        self.is_recording = False
        
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
            
            # Set buffer size to minimize latency
            self.usb_camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
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
    
    def record_synchronized_frames(self, duration_seconds, output_path="recordings"):
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        self.is_recording = True
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tof_filename = os.path.join(output_path, f"tof_sync_{timestamp}.mp4")
        usb_filename = os.path.join(output_path, f"usb_sync_{timestamp}.mp4")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        tof_writer = None
        usb_writer = None
        
        start_time = time.time()
        frame_count = 0
        sync_failures = 0
        tof_failures = 0
        usb_failures = 0
        both_failures = 0
        
        print(f"Starting synchronized frame recording for {duration_seconds} seconds...")
        print("Recording frames in perfect sync...")
        print("Debug: Detailed sync failure tracking enabled")
        
        try:
            while self.is_recording and (time.time() - start_time) < duration_seconds:
                # Capture timestamp for synchronization
                capture_time = time.time()
                
                # Capture from both cameras simultaneously
                tof_frame = None
                usb_frame = None
                tof_success = False
                usb_success = False
                
                # Try to get ToF frame
                tof_start = time.time()
                try:
                    ac_frame = self.tof_camera.requestFrame(200)  # Short timeout for sync
                    if ac_frame is not None and isinstance(ac_frame, ac.RawData):
                        buf = ac_frame.raw_data
                        self.tof_camera.releaseFrame(ac_frame)
                        
                        # Convert to 8-bit format for saving
                        buf_8bit = (buf / (1 << 4)).astype(np.uint8)
                        
                        # Convert to color format for video saving
                        if len(buf_8bit.shape) == 2:
                            tof_frame = cv2.cvtColor(buf_8bit, cv2.COLOR_GRAY2BGR)
                        else:
                            tof_frame = buf_8bit
                        
                        tof_success = True
                    else:
                        print(f"Debug: ToF requestFrame returned None or invalid type")
                except Exception as e:
                    print(f"Debug: ToF frame capture exception: {e}")
                tof_time = time.time() - tof_start
                
                # Try to get USB frame
                usb_start = time.time()
                try:
                    ret, usb_frame = self.usb_camera.read()
                    if ret and usb_frame is not None:
                        usb_success = True
                    else:
                        print(f"Debug: USB camera read failed - ret: {ret}, frame is None: {usb_frame is None}")
                except Exception as e:
                    print(f"Debug: USB frame capture exception: {e}")
                usb_time = time.time() - usb_start
                
                # Debug timing information
                if frame_count % 100 == 0:  # Print every 100th frame
                    print(f"Debug: Frame {frame_count} - ToF: {tof_time*1000:.1f}ms, USB: {usb_time*1000:.1f}ms, ToF OK: {tof_success}, USB OK: {usb_success}")
                
                # Only save if both frames were captured successfully
                if tof_success and usb_success:
                    # Initialize video writers with actual frame dimensions
                    if tof_writer is None and tof_frame is not None:
                        height, width = tof_frame.shape[:2]
                        tof_writer = cv2.VideoWriter(tof_filename, fourcc, 20.0, (width, height))
                        print(f"ToF video writer initialized: {width}x{height}")
                    
                    if usb_writer is None and usb_frame is not None:
                        height, width = usb_frame.shape[:2]
                        usb_writer = cv2.VideoWriter(usb_filename, fourcc, self.usb_fps, (width, height))
                        print(f"USB video writer initialized: {width}x{height}")
                    
                    # Write both frames
                    if tof_writer and tof_frame is not None:
                        tof_writer.write(tof_frame)
                    
                    if usb_writer and usb_frame is not None:
                        usb_writer.write(usb_frame)
                    
                    frame_count += 1
                else:
                    sync_failures += 1
                    
                    # Track specific failure types
                    if not tof_success and not usb_success:
                        both_failures += 1
                        print(f"Debug: Frame {frame_count + sync_failures} - BOTH cameras failed")
                    elif not tof_success:
                        tof_failures += 1
                        print(f"Debug: Frame {frame_count + sync_failures} - ToF camera failed")
                    elif not usb_success:
                        usb_failures += 1
                        print(f"Debug: Frame {frame_count + sync_failures} - USB camera failed")
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.001)
                
                # Control frame rate - aim for consistent timing
                frame_time = time.time() - capture_time
                target_frame_time = 1.0 / 20.0  # 20 FPS target
                if frame_time < target_frame_time:
                    time.sleep(target_frame_time - frame_time)
        
        except KeyboardInterrupt:
            print("\nStopping recording...")
            self.is_recording = False
        
        finally:
            if tof_writer:
                tof_writer.release()
            if usb_writer:
                usb_writer.release()
        
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        sync_success_rate = (frame_count / (frame_count + sync_failures)) * 100 if (frame_count + sync_failures) > 0 else 0
        
        print(f"\nSynchronized recording completed:")
        print(f"  Duration: {elapsed_time:.2f} seconds")
        print(f"  Synchronized frames: {frame_count}")
        print(f"  Sync failures: {sync_failures}")
        print(f"    - ToF only failures: {tof_failures}")
        print(f"    - USB only failures: {usb_failures}")
        print(f"    - Both failed: {both_failures}")
        print(f"  Sync success rate: {sync_success_rate:.1f}%")
        print(f"  Average FPS: {fps:.2f}")
        print(f"  ToF video: {tof_filename}")
        print(f"  USB video: {usb_filename}")
        
        return {
            "tof_file": tof_filename,
            "usb_file": usb_filename,
            "duration": elapsed_time,
            "frame_count": frame_count,
            "sync_failures": sync_failures,
            "sync_success_rate": sync_success_rate,
            "fps": fps
        }
    
    def stop_recording(self):
        self.is_recording = False
    
    def close(self):
        self.stop_recording()
        
        if self.tof_camera:
            self.tof_camera.stop()
            self.tof_camera.close()
        
        if self.usb_camera:
            self.usb_camera.release()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Synchronized Frame Recorder - ToF and USB cameras')
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
    
    recorder = SyncFrameRecorder(
        usb_camera_index=args.usb_camera,
        usb_resolution=(args.usb_width, args.usb_height),
        usb_fps=args.usb_fps
    )
    
    try:
        recorder.initialize_cameras()
        results = recorder.record_synchronized_frames(args.duration, args.output)
        
        print("\n" + "="*50)
        print("SYNCHRONIZED RECORDING SUMMARY")
        print("="*50)
        
        if results:
            print(f"Status: SUCCESS")
            for key, value in results.items():
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        recorder.close()

if __name__ == "__main__":
    main()