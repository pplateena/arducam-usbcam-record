import cv2
import numpy as np
import ArducamDepthCamera as ac
import time
import os
from datetime import datetime


def record_video(duration_seconds=10, output_path="recordings"):
    print("Arducam Depth Camera Video Recording")
    print("  SDK version:", ac.__version__)
    
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_path, f"tof_raw_{timestamp}.avi")

    cam = ac.ArducamCamera()
    cfg_path = None
    
    ret = 0
    if cfg_path is not None:
        ret = cam.openWithFile(cfg_path, 0)
    else:
        ret = cam.open(ac.Connection.CSI, 0)
    if ret != 0:
        print("initialization failed. Error code:", ret)
        return None

    ret = cam.start(ac.FrameType.RAW)
    if ret != 0:
        print("Failed to start camera. Error code:", ret)
        cam.close()
        return None

    # Video writer setup
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    writer = None
    
    start_time = time.time()
    frame_count = 0
    
    print(f"Recording for {duration_seconds} seconds...")
    print("Press 'q' to stop recording early")
    
    try:
        while (time.time() - start_time) < duration_seconds:
            frame = cam.requestFrame(2000)
            if frame is not None and isinstance(frame, ac.RawData):
                buf = frame.raw_data
                cam.releaseFrame(frame)

                # Convert to 8-bit format for display and saving
                buf_8bit = (buf / (1 << 4)).astype(np.uint8)
                
                # Convert to color format for video saving (grayscale to BGR)
                if len(buf_8bit.shape) == 2:
                    buf_colored = cv2.cvtColor(buf_8bit, cv2.COLOR_GRAY2BGR)
                else:
                    buf_colored = buf_8bit
                
                # Initialize video writer with actual frame dimensions
                if writer is None:
                    height, width = buf_colored.shape[:2]
                    writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
                    print(f"Video writer initialized: {width}x{height}")
                
                # Write frame to video
                writer.write(buf_colored)
                frame_count += 1
                
                # Display frame
                cv2.imshow("Recording - Press 'q' to stop", buf_8bit)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("Recording stopped by user")
                break

    finally:
        if writer:
            writer.release()
        cv2.destroyAllWindows()
        cam.stop()
        cam.close()
    
    elapsed_time = time.time() - start_time
    fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    
    print(f"Recording completed:")
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


def preview_only():
    print("Arducam Depth Camera Preview")
    print("  SDK version:", ac.__version__)

    cam = ac.ArducamCamera()
    cfg_path = None

    ret = 0
    if cfg_path is not None:
        ret = cam.openWithFile(cfg_path, 0)
    else:
        ret = cam.open(ac.Connection.CSI, 0)
    if ret != 0:
        print("initialization failed. Error code:", ret)
        return

    ret = cam.start(ac.FrameType.RAW)
    if ret != 0:
        print("Failed to start camera. Error code:", ret)
        cam.close()
        return

    print("Preview mode - Press 'q' to quit")
    
    while True:
        frame = cam.requestFrame(2000)
        if frame is not None and isinstance(frame, ac.RawData):
            buf = frame.raw_data
            cam.releaseFrame(frame)

            buf = (buf / (1 << 4)).astype(np.uint8)

            cv2.imshow("Preview - Press 'q' to quit", buf)

        key = cv2.waitKey(1)
        if key == ord("q"):
            break

    cam.stop()
    cam.close()
    cv2.destroyAllWindows()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Arducam ToF Camera Recorder')
    parser.add_argument('--record', action='store_true', help='Record video instead of preview')
    parser.add_argument('--duration', type=int, default=10, help='Recording duration in seconds (default: 10)')
    parser.add_argument('--output', type=str, default='recordings', help='Output directory (default: recordings)')
    
    args = parser.parse_args()
    
    if args.record:
        result = record_video(args.duration, args.output)
        if result:
            print("Recording successful!")
        else:
            print("Recording failed!")
    else:
        preview_only()


if __name__ == "__main__":
    main()