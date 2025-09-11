# arducam-usbcam-record
Project that allows to capture and save 2 videos from ToF camera in sync with default camera on raspberry pi

## Project Structure
- `tof_recorder.py` - Arducam ToF camera recording module (depth and amplitude)
- `usb_recorder.py` - USB camera recording module
- `dual_camera_recorder.py` - Main synchronized recording system
- `test_cameras.py` - Camera functionality test utility
- `requirements.txt` - Python dependencies

## Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

Additionally, you need to install the ArducamDepthCamera library:
- Follow the installation guide at: https://github.com/ArduCAM/Arducam_tof_camera
- Run the provided `Install_dependencies.sh` script

## Usage

### Test Cameras
First, verify both cameras are working:
```bash
python test_cameras.py
```

### Record Videos
Record synchronized videos from both cameras:
```bash
# Record for 10 seconds (default)
python dual_camera_recorder.py

# Record for 30 seconds
python dual_camera_recorder.py --duration 30

# Custom output directory
python dual_camera_recorder.py --duration 15 --output my_recordings

# Full options
python dual_camera_recorder.py --duration 20 --output recordings --usb-camera 0 --max-distance 4000 --usb-width 1280 --usb-height 720 --usb-fps 30
```

### Individual Camera Recording
You can also record from cameras individually:

```bash
# ToF camera only
python tof_recorder.py

# USB camera only
python usb_recorder.py
```

## Output Files
The system creates timestamped video files:
- `tof_depth_YYYYMMDD_HHMMSS.avi` - ToF depth data (color-mapped)
- `tof_amplitude_YYYYMMDD_HHMMSS.avi` - ToF amplitude data
- `usb_camera_YYYYMMDD_HHMMSS.avi` - USB camera video

All files are saved in the specified output directory (default: `recordings/`)

