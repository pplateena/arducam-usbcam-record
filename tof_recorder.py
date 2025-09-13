#!/usr/bin/env python3

import sys
import cv2
import numpy as np
import ArducamDepthCamera as ac
import os
from datetime import datetime


def save_raw_data(depth_data, confidence_data, amplitude_data, frame_number):
    """Save raw data to files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create output directory
    output_dir = f"tof_raw_data_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # Save as numpy arrays
    np.save(os.path.join(output_dir, f"depth_{frame_number:04d}.npy"), depth_data)
    np.save(os.path.join(output_dir, f"confidence_{frame_number:04d}.npy"), confidence_data)

    if amplitude_data is not None:
        np.save(os.path.join(output_dir, f"amplitude_{frame_number:04d}.npy"), amplitude_data)

    # Save as CSV for easy reading
    np.savetxt(os.path.join(output_dir, f"depth_{frame_number:04d}.csv"),
               depth_data, delimiter=',', fmt='%.3f')

    print(f"Saved frame {frame_number} to {output_dir}/")
    return output_dir


def capture_single_frame(cam):
    """Capture a single frame and return data"""
    frame = cam.requestFrame(1000)  # 1 second timeout
    if frame is None:
        return None, None, None

    # Get raw data
    depth_data = frame.getDepthData()
    confidence_data = frame.getConfidenceData()

    # Try to get amplitude data (may not be available on all models)
    try:
        amplitude_data = frame.getAmplitudeData()
    except:
        amplitude_data = None

    # Convert to numpy arrays
    if depth_data is not None:
        depth_array = np.array(depth_data, dtype=np.float32).reshape(180, 240)
    else:
        depth_array = None

    if confidence_data is not None:
        confidence_array = np.array(confidence_data, dtype=np.float32).reshape(180, 240)
    else:
        confidence_array = None

    if amplitude_data is not None:
        amplitude_array = np.array(amplitude_data, dtype=np.float32).reshape(180, 240)
    else:
        amplitude_array = None

    cam.releaseFrame(frame)
    return depth_array, confidence_array, amplitude_array


def continuous_capture(cam, num_frames=10):
    """Capture multiple frames continuously"""
    print(f"Starting continuous capture of {num_frames} frames...")

    output_dir = None
    for i in range(num_frames):
        print(f"Capturing frame {i + 1}/{num_frames}...")

        depth_data, confidence_data, amplitude_data = capture_single_frame(cam)

        if depth_data is None:
            print(f"Failed to capture frame {i + 1}")
            continue

        # Save the data
        if output_dir is None:
            output_dir = save_raw_data(depth_data, confidence_data, amplitude_data, i + 1)
        else:
            save_raw_data(depth_data, confidence_data, amplitude_data, i + 1)

        # Show basic stats
        if depth_data is not None:
            valid_depths = depth_data[~np.isnan(depth_data)]
            if len(valid_depths) > 0:
                print(f"  Depth range: {valid_depths.min():.3f}m - {valid_depths.max():.3f}m")
                print(f"  Average depth: {valid_depths.mean():.3f}m")
                print(f"  Valid pixels: {len(valid_depths)}/{depth_data.size}")

    print(f"Capture complete. Data saved to: {output_dir}/")


def main():
    """Main function"""
    print("ArduCAM ToF Camera - Raw Data Capture")
    print("====================================")

    # Initialize camera
    cam = ac.ArducamCamera()

    # Try to connect
    print("Initializing camera...")
    try:
        if cam.init(ac.TOFConnect.CSI, ac.TOFOutput.DEPTH) != 0:
            print("CSI connection failed, trying USB...")
            if cam.init(ac.TOFConnect.USB, ac.TOFOutput.DEPTH) != 0:
                print("ERROR: Failed to initialize camera on both CSI and USB")
                return -1
            else:
                print("✓ Camera initialized via USB")
        else:
            print("✓ Camera initialized via CSI")
    except Exception as e:
        print(f"ERROR: Exception during initialization: {e}")
        return -1

    # Start camera
    if cam.start() != 0:
        print("ERROR: Failed to start camera")
        return -1

    print("✓ Camera started")

    try:
        while True:
            print("\nOptions:")
            print("1. Capture single frame")
            print("2. Capture multiple frames (continuous)")
            print("3. Test camera connection")
            print("4. Exit")

            choice = input("Enter choice (1-4): ").strip()

            if choice == '1':
                print("Capturing single frame...")
                depth_data, confidence_data, amplitude_data = capture_single_frame(cam)

                if depth_data is not None:
                    save_raw_data(depth_data, confidence_data, amplitude_data, 1)

                    # Show basic info
                    valid_depths = depth_data[~np.isnan(depth_data)]
                    if len(valid_depths) > 0:
                        print(f"✓ Frame captured successfully")
                        print(f"  Resolution: {depth_data.shape}")
                        print(f"  Depth range: {valid_depths.min():.3f}m - {valid_depths.max():.3f}m")
                        print(f"  Valid pixels: {len(valid_depths)}/{depth_data.size}")
                else:
                    print("✗ Failed to capture frame")

            elif choice == '2':
                try:
                    num_frames = int(input("Number of frames to capture: "))
                    if num_frames > 0:
                        continuous_capture(cam, num_frames)
                    else:
                        print("Invalid number of frames")
                except ValueError:
                    print("Please enter a valid number")

            elif choice == '3':
                print("Testing camera connection...")
                depth_data, confidence_data, amplitude_data = capture_single_frame(cam)

                if depth_data is not None:
                    print("✓ Camera is working properly")
                    print(f"  Data shape: {depth_data.shape}")
                    print(f"  Data type: {depth_data.dtype}")
                    print(f"  Has confidence data: {confidence_data is not None}")
                    print(f"  Has amplitude data: {amplitude_data is not None}")
                else:
                    print("✗ Camera test failed")

            elif choice == '4':
                break

            else:
                print("Invalid choice")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        print("Stopping camera...")
        cam.stop()
        print("Done.")


if __name__ == "__main__":
    main()