# CARLA VIDEO DATA GENERATION FOR OBJECT DETECTION

Aim of this project is to generate video data and annotations for object detection. The system consists of two subparts, the server and the client. The server handles the simulation and rendering of video frames. Client spawns objects (vehicles, pedestrians and a camera). The camera of the client is a mobile object that follows a specified trajectory. While the camer is moving, video frames and object locations inside the frames are logged. After the client disconnects, the video file and its annotation file will be given to the user.

## Directory and File Structure
Main and helper scripts for this project are in the root directory. Purpose of each file are:
- **auto.sh**: Iteratively calls the main.py which initiates the client connection to the server. After the client is finished collecting certain amount of data, main.py will be called again.
- **config.py**: Configuration file containing CARLA parameters (filter values for segmentation masks).
- **helper.py**: Helper functions used in the camera frame processing.
- **main.py**: Main script which initiates a connection to the server.
- **recorder.py**: Contains Recorder class implementation which is used to capture frames from the server.
- **video_labeler.py**: Called when the connection is broken/closed/interrupted. This script handles the merging operation for the video and the annotation file. In the end, another video is generated on which the bounding boxes of the objects are selected.
- **out/**: Directory containing the generated data files.
- **dist/**: Contains CARLA module .egg files which are loaded by the main script if they are not installed on the system.

## How to run?

Before starting the client, which generates video data and annotation, the server must be launched. The server is assumed to be installed as a container. Therefore, as it is given on the CARLA docs, the server is started with the command:

`docker run -p 2000-2002:2000-2002 --runtime=nvidia --gpus all carlasim/carla:0.9.2`

Once the server is started, the client can be called to start generating video data. The client can be started with the following command for a single video generation: 
`python3 main.py 1`

where 1 is an index number for video file generation. If more than one video should be generated, this is automated with the auto.sh script. This script is ran with the following command:
`bash auto.sh &`

## How does the system work?
When the server is launched, it will wait for a client to connect. When the user wants to generate data, the client will connect to the server and acquire the control of the tick times. This is necessary to synchronize the server frames and the client frames as frame processing on the client side is a time consuming procedure. Unfortunately, giving the control to the client prevents the parallelization of the video generation by several clients connected simultaneously.

When the cleint obtains the control, it will start generating specified amount of vehicles and pedestrians on the server. Later, a camera recorder object (Recorder class in recorder.py) will be initialized. This object iteratively captures frames obtained by the camera object in the server world. These frames are appended to a video. Moreover, segmentation mask (which is available in CARLA with mask values in config.py) will be applied to discriminate different objects. Using the segmentation mask, pedestrians and vehicle bounding boxes will be computed using contour detection. Bounding box locations and sizes will be appended to a log file tagged with corresponding server time.

When the data generation time is finished, the video file of frames will be dumped in .mp4 format. Also, the information about the bounding boxes through time will be dumped to a .json file. Both of these files can be found at out/ directory.

When all these steps are finished, video_labeler.py will be called, which generates an annotated video for the visualization purposes.

## How to configure the data generation?
There are certain parameters in this system that the user can change to yield different video data ath the output.

### Output file location
Output file for annotation and video data are given in the main.py as:
```python
info_file = "~/PycharmProjects/carla/out/info_{}.txt".format(order)
video_file = "~/PycharmProjects/carla/out/video_{}.mp4".format(order)
log_file = "~/PycharmProjects/carla/out/log_{}.csv".format(order)
labeled_file = "~/PycharmProjects/carla/out/labeled_{}.mp4".format(order)
```

### Server IP and Port
Server IP and Port is also selected from the main.py as:
```python
client = carla.Client('192.168.12.211', 2000)
client.set_timeout(10.0)
```

### FPS for video data
It is possible to change the FPS from the main.py as:
```python
fps  =  0.033
```
where fps is selected as the frame period in seconds.

### Number of Vehicles on Server
It is possible to change the number of vehicles on the server during the generation from the main.py as:
```python
num_vehics =  10
```
### Simulation time
Total video lenght/number of frames for each run can be specified from main.py using the parameter:
```python
end_step = 15000
```
where end_steps is selected as the total number of frames for a single video.

### Video Resolution
Video resolution can be changed from the recorder.py as:
```python
VIDEO_RES  = (1440, 2560)
```

### Camera Trajectory During Videos
It is possible to change the trajectory of the camer flying over the server world. This is handled by a method of the Recorder class which is located in the recorder.py script. This method uses the **cur_pos**, **cur_velocity** and **cur_angle** of the recorder object to generate the new position and transform the camera to that location. This method is **move** which does not accept any arguments. Three vectors describing the location and the orientation of the camera are:
- **cur_pos**: vector with three elements (x, y, z) coordinates of the camera object.
- **cur_angle**: vector with three elements (y, p, r) orientations (yaw, pitch, roll). 
- **cur_velovity**: vector with 4 elements (Vx, Vy, w_y, w_p) in 2 directions and 2 orientations.
