#!/usr/bin/env python3

import sys
import cv2

def test_usb_camera(camera_index=0):
    print(f"Testing USB camera at index {camera_index}...")
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"  ERROR: Cannot open USB camera at index {camera_index}")
        return False
    
    ret, frame = cap.read()
    if not ret:
        print(f"  ERROR: Cannot read frame from USB camera at index {camera_index}")
        cap.release()
        return False
    
    height, width = frame.shape[:2]
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"  SUCCESS: USB camera working")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    
    cap.release()
    return True

def test_tof_camera():
    print("Testing Arducam ToF camera...")
    
    try:
        import ArducamDepthCamera as ac
    except ImportError:
        print("  ERROR: ArducamDepthCamera library not found")
        print("  Please install the ArducamDepthCamera library")
        print("  Visit: https://github.com/ArduCAM/Arducam_tof_camera")
        return False
    
    camera = ac.ArducamCamera()
    
    if camera.open(ac.TOFConnect.CSI, 0) != 0:
        if camera.open(ac.TOFConnect.USB, 0) != 0:
            print("  ERROR: Cannot open ToF camera (tried both CSI and USB)")
            return False
        else:
            print("  SUCCESS: ToF camera opened via USB")
    else:
        print("  SUCCESS: ToF camera opened via CSI")
    
    ret = camera.start(ac.TOFOutput.DEPTH)
    if ret != 0:
        print("  ERROR: Cannot start ToF camera")
        camera.close()
        return False
    
    frame = camera.requestFrame(1000)
    if frame is None:
        print("  ERROR: Cannot capture frame from ToF camera")
        camera.stop()
        camera.close()
        return False
    
    print("  SUCCESS: ToF camera working")
    print("  Frame captured successfully")
    
    camera.releaseFrame(frame)
    camera.stop()
    camera.close()
    return True

def main():
    print("Camera Test Utility")
    print("=" * 40)
    
    usb_ok = test_usb_camera()
    print()
    tof_ok = test_tof_camera()
    
    print("\n" + "=" * 40)
    print("TEST RESULTS:")
    print(f"USB Camera: {'PASS' if usb_ok else 'FAIL'}")
    print(f"ToF Camera: {'PASS' if tof_ok else 'FAIL'}")
    
    if usb_ok and tof_ok:
        print("\nAll cameras working! You can now run the recorder.")
        print("Usage: python dual_camera_recorder.py --duration 10")
        sys.exit(0)
    else:
        print("\nSome cameras failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()