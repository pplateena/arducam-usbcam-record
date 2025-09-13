import cv2
import time
import os
from datetime import datetime

def detect_cameras(max_index=10):
    """Detect available cameras and return working indices"""
    available_cameras = []
    
    print("Detecting available cameras...")
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f"  Camera {i}: WORKING - {width}x{height} @ {fps} FPS")
                available_cameras.append(i)
                
                # Show a preview frame for 1 second
                cv2.imshow(f"Camera {i} Preview", frame)
                cv2.waitKey(1000)
                cv2.destroyAllWindows()
            else:
                print(f"  Camera {i}: detected but cannot read frames")
        else:
            pass  # Camera not available at this index
        cap.release()
    
    if not available_cameras:
        print("No working cameras found!")
    else:
        print(f"Found {len(available_cameras)} working cameras: {available_cameras}")
    
    return available_cameras

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
        filename = os.path.join(output_path, f"usb_camera_{timestamp}.mp4")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
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

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='USB Camera Recorder')
    parser.add_argument('--detect', action='store_true', help='Detect available cameras')
    parser.add_argument('--record', action='store_true', help='Record video')
    parser.add_argument('--preview', action='store_true', help='Preview camera (default if no other action specified)')
    parser.add_argument('--camera', type=int, default=0, help='Camera index (default: 0)')
    parser.add_argument('--duration', type=int, default=10, help='Recording duration in seconds (default: 10)')
    parser.add_argument('--output', type=str, default='recordings', help='Output directory (default: recordings)')
    parser.add_argument('--width', type=int, default=1280, help='Camera width (default: 1280)')
    parser.add_argument('--height', type=int, default=720, help='Camera height (default: 720)')
    parser.add_argument('--fps', type=int, default=30, help='Camera FPS (default: 30)')
    
    args = parser.parse_args()
    
    if args.detect:
        available_cameras = detect_cameras()
        if available_cameras:
            print(f"\nRecommended usage:")
            for cam_id in available_cameras:
                print(f"  python usb_recorder.py --record --camera {cam_id}")
        return
    
    if not args.record and not args.preview:
        args.preview = True  # Default to preview mode
    
    recorder = USBRecorder(
        camera_index=args.camera,
        resolution=(args.width, args.height),
        fps=args.fps
    )
    
    try:
        print(f"Using camera index: {args.camera}")
        recorder.initialize_camera()
        
        if args.record:
            result = recorder.record_video(args.duration, args.output)
            if result:
                print("Recording successful!")
            else:
                print("Recording failed!")
        elif args.preview:
            print("Preview mode - Press 'q' to quit")
            recorder.camera = cv2.VideoCapture(args.camera)
            if not recorder.camera.isOpened():
                print(f"Failed to open camera {args.camera}")
                return
            
            while True:
                ret, frame = recorder.camera.read()
                if ret:
                    cv2.imshow('USB Camera Preview - Press q to quit', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    print("Failed to read frame")
                    break
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        recorder.close()

if __name__ == "__main__":
    main()