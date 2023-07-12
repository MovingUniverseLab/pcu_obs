# pcu_obs
A script to take distortion observations with the PCU.
It can be run on an OSIRIS computer.
Before observing it sets the filter and integration time on OSIRIS
It takes observations in a square grid, covering XY positons and rotation angles.
After observing the grid it takes a dark observation with the same integration time.
The FITS files are saved in the usual OSIRIS location, e.g. /s/sdata1100/osiris6/230405/IMAG/raw
Log files are saved in the current directory, with the timestamp in the name: PCU_YYYYMMDD_HHMMSS.log


**Change parameters**
You can set up the parameters for the run by modifying the variables at the top of the script, in the section -------Adjustable Parameters----------

	mode				- A flag to quickly switch between different sets of parameters, like distortion and phase diversty.
	filter_band 		- The filter to use. Must match an OSIRIS filter keyword. Default='Hbb'
	dither_spacing 		- The spacing in mm that the PCU moves bewteen each grid position. Default=6.16 for a 3x3 grid.
	dither_grid_size 	- The number of points in the grid. Default=3 giving a 3x3 grid.	
	rotation_angles 	- A list of the rotation angles of the pinhole mask in degrees. Default=[0,30,90]
	focus_positions 	- The Z positions to take observations at. Used for phase diversity. Default=[pinhole_focus] Max Z is 102.
	integration_time 	- OSIRIS integration time in seconds. One for each Z position. Default=['10'] for dome flat position, ['60'] for horizon stow position.
	repeats 			- Number of images to take at each grid position. Default=1


**Operation**

1) Get take_distortion_obs.py onto the OSIRIS machine.
	May need to do Keck authentication in a browser.
	Send take_distorion_obs.py from your machine with scp

2) Launch the PCU GUI:
	May need to connect to a machine with AO access, using ssh -X
	k1pcu_seq.dsp

3) Have the telscope in dome flat position, and set the dome lamps to max (0):
	lamp dome 0

4) Run the script:
	kpython3 take_distortion_obs.py
	It will take the observations, take a dark, and save a log file.

5) Stow the PCU when you're done:
	In the PCU GUI dropdown menu, select HOME, and click GO.

5) Download the data and log files to your machine using scp.
	Do Keck authenticaiton in browser.
	Images are in the usual place, eg /s/sdata1100/osiris6/230405/IMAG/raw
	Log files are in /home/osiris, use *.log with scp



**Notes**

Orientation:
Positive X movement of the PCU = Positive X movement of the pinholes in the raw images
Positive Y movement of the PCU = Positive Y movement of the pinholes in the raw images (So negative Y in the flipped images)
Positive Z movement of the PCU = Further into the K-mirror (the PCU is mounted on the front of the bench)
Positive R rotation of the PCU = Clockwise rotation of the pinholes in the raw images (so anticlockwise in the flipped images)

Limits:
The safe limit for the pinhole mask is a 12mm radius from the on-axis position of X=90,Y=185. So the max grid is 16.8mm on a side.
The maxium Z position is 102mm

Filters:
Tests with the Kp filter show a lot of the dust/marks on the pinhole mask surface, probably due to IR emission. The Hbb filter is closer to visible, so we see less of that.

Scale:
The pinholes are 0.5mm apart
OSIRIS image scale = 138.5 pixels per mm on the pinhole mask.

Dithers
We want pairs of points to be imaged on opposite sides of the detector. Say 10% in from each edge = 1843 pixels ~ 13.2mm
Suggested dither_spacing = 6.6mm for 3x3
						 = 3.3mm for 5x5
Avoid a multiple of 0.5mm so that pinholes are not imaged at the same detector positions (we would prefer to sample more areas).

Manually controlling the PCU:
You can command the PCU with the GUI either by selecting a named position and clicking GO, or typing an X/Y/Z coordinate and clicking GO. There are fields for absolute moves, and moves relative to the current position.
The named positions are in the dropdown menu on the top left. The relevant ones for us are PINHOLE_MASK (the on-axis position for taking pinhole observations), and HOME (stows the PCU away to the side when you are finished). 
To take manual pinhole observations, move to PINHOLE_MASK, then make finer moves from there. There is collision avoidance software running, so you shouldn't be able to crash into anything. 
The rotation stage is not in the GUI. You can command its position with Keck Keywords from any terminal:
Read: 		Show -s ao1 PCUPR
Write: 		Modify -s ao1 PCUPR=65.703 		(The default angle is 65.703, assuming the K-mirror is in the default position)
The keywords replace the older EPICS commands:
Read:		caget k1:ao:pcu:rot:posvalRb		        
Write:		caput k1:ao:pcu:rot:posval 65.703		     


