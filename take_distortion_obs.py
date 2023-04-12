# This script takes a series of images of the PCU with OSIRIS, for the purpose of distortion calibration.
# By Matthew Freeman 2023
# Using Avinash Surendran's blockMove functions

import numpy as np
import subprocess
import time
import sys
import ktl
#import epics
import logging
from datetime import datetime

 #--------- Dither Pattern -------------
dither_spacing = 6.16 #mm   #6.16 for 3x3, 3.1 for 5x5
dither_grid_size = 1  # e.g. 5 = 5x5 grid
position_angles =[0,45,90] # e.g. [0, 45] degrees
pinhole_x = 90  #x_stage location for the centre of the dither pattern
pinhole_y = 185
#max radius = 12mm -> max grid extent = 16.8mm
integration_time = '10' #'10' for dome flat postion, '60' for horizon with tertiary not aligned
#--------------------------------------

#-------------Keck Keywords--------------
keck_kw = { 'ao':'ao1',
			#'m1':'PCUM1POS',      #Duplicates of x,y,z?
			#'m2':'PCUM2POS',
			#'m3':'PCUM3POS',
			'r':'PCUPR',
			'x':'PCSFX',           #PCUX
			'y':'PCSFY',           #PCUY
			'z':'PCSFUZ',           #PCULZ
			'state':'PCSFSTATE',    #PCUSTATE 
			'status':'PCSFSTST',
			#'r_status':'PCURSTST',  #may show the same as status? Check if needed when doing rotational blocking moves.
			'named_pos':'PCSFNAME',  #PCUNAME
			'pinhole':'pinhole_mask',		
			}
#----------------------------------------

#---------epics keywords---------------
#pcu_status = epics.PV('k1:ao:pcu:stst')
#pcu_request = epics.PV('k1:ao:pcu:request')
#pcu_x = {'name':'x','write':epics.PV('k1:ao:pcu:M1Pos'),'read':epics.PV('k1:ao:pcu:M1Pos')}
#pcu_y = {'name':'y','write':epics.PV('k1:ao:pcu:M2Pos'),'read':epics.PV('k1:ao:pcu:M2Pos')}
#pcu_uz = {'name':'uz','write':epics.PV('k1:ao:pcu:M3Pos'),'read':epics.PV('k1:ao:pcu:M3Pos')}
#pcu_r = {'name':'r','write':epics.PV('k1:ao:pcu:rot:pos'),'read':epics.PV('k1:ao:pcu:rot:pos Rb')}
#--------------------------------------

def main():
	extent = (dither_grid_size-1) * dither_spacing /2
	grid_steps_x = np.linspace(pinhole_x-extent,pinhole_x+extent,dither_grid_size)
	grid_steps_y = np.linspace(pinhole_y-extent,pinhole_y+extent,dither_grid_size)
	print('X grid steps = {}'.format(grid_steps_x))
	print('Y grid steps = {}'.format(grid_steps_y))
	check_limits(grid_steps_x,grid_steps_y,pinhole_x,pinhole_y)
	total_frames = len(grid_steps_x) * len(grid_steps_y) * len(position_angles)
	subprocess.run(['lamp', 'dome', '0'])  
	subprocess.run(['iitime', integration_time])
	subprocess.run(['icoadds', '1'])  
	#subprocess.run(['insamp', '4']) 		#readout mode
	print('(Set K rotator to 225?)')
	# subprocess.run(['modify','-s','ao','obtdname=' + 'open'])   #Set TRICK to open or hband, takes 60 seconds.
	# time.sleep(60) 
	# subprocess.run(['ifilt', 'kp', 'open'])     #Set filter. eg 'Drk' or 'kp open' 
	# time.sleep(10)
	make_log()
	log_entry('Filename','x','y','z','r','type')

	#-----------starting moves-----------------
	blockMoveNP(keck_kw['pinhole'])
	blockMove(keck_kw['z'],99.32)
	frame_number = 1
	for angle in position_angles:
		blockMove(keck_kw['r'],65.7 + angle)
		direction = 1
		for y in grid_steps_y:
			blockMove(keck_kw['y'],y)	
			for x in grid_steps_x[::direction]:
				blockMove(keck_kw['x'],x)	
				print('Taking frame {}/{}'.format(frame_number,total_frames))
				img_filename = take_image()
				frame_number+=1
				img_filename = img_filename[-20:]
				pcux = ktl.read(keck_kw['ao'], keck_kw['x'])
				pcuy = ktl.read(keck_kw['ao'], keck_kw['y'])
				pcupz = ktl.read(keck_kw['ao'], keck_kw['z'])
				pcur = ktl.read(keck_kw['ao'], keck_kw['r'])
 				#pcur = '65.7005'
				log_entry(img_filename,pcux,pcuy,pcupz,pcur,'pinhole')
			direction*=-1
	print('Finished taking images. Time='+ datetime.now().strftime('%H%M%S'))
  

def blockMove(keyword, position):
	print('Moving {} to {}'.format(keyword, position))
	ktl.write(keck_kw['ao'], keyword, position)
	time.sleep(2)
	while True:
		pcu = ktl.read(keck_kw['ao'], keyword)
		status = ktl.read(keck_kw['ao'], keck_kw['status'])
		print(keyword +' is at ' + str(pcu) + ' and PCU state is ' + status)
		if status == 'INPOS':
			print(keyword +' has reached designated position')
			return
		elif status == 'FAULT':
			sys.exit('Stage has FAULTED, exiting program..')
		time.sleep(2)

def blockMoveNP(target):
	print('Moving to named position {}'.format(target))
	ktl.write(keck_kw['ao'], keck_kw['named_pos'], target)
	time.sleep(2)
	while True:
		pcux = ktl.read(keck_kw['ao'], keck_kw['x'])
		pcuy = ktl.read(keck_kw['ao'], keck_kw['y'])
		pculz = ktl.read(keck_kw['ao'], keck_kw['z'])
		status = ktl.read(keck_kw['ao'], keck_kw['status'])
		print('PCUX = ' + pcux + ', PCUY = ' + pcuy + ', PCUZ = ' + pculz + ' and PCU state is ' + status)
		if status == 'INPOS':
			print('Stage has reached designated position')
			return
		elif status == 'FAULT':
			sys.exit('Stage has FAULTED, exiting program..')
		time.sleep(2)

def take_image(n=1):
	subprocess.run(['igoi',str(n)],check='True')
	filename = ktl.read('oids','lastfile')
	# filename = subprocess.run(['lastimage'],capture_output=True,text=True)
	return filename

def make_log():
	log_filename = datetime.now().strftime('PCU_%Y%m%d_%H%M%S.log')
	print('Log filename:', log_filename)
	logging.basicConfig(filename=log_filename, level=logging.INFO,format='%(message)s')

def log_entry(filename,x,y,z,r,flag):
	logging.info('{:>10} {:>10} {:>10} {:>10} {:>10} {:>10}'.format(filename,x,y,z,r,flag))


def check_limits(x_grid,y_grid,x_pinhole,y_pinhole):
	#the function checks that all grid positions are with a 12 mm radius from the central position
	radius_limit = 12
	for x in x_grid:
		for y in y_grid:
			radius = np.hypot(x-x_pinhole,y-y_pinhole)
			if radius > radius_limit:
				print('Grid position {},{} is outside the {}mm radius from {},{}'.format(x,y,radius_limit,x_pinhole,y_pinhole))
				print('Aborting')
				sys.exit(0)

def main_epics():
	extent = (dither_grid_size-1) * dither_spacing /2
	grid_steps_x = np.linspace(pinhole_x-extent,pinhole_x+extent,dither_grid_size)
	grid_steps_y = np.linspace(pinhole_y-extent,pinhole_y+extent,dither_grid_size)
	print('X grid steps = {}'.format(grid_steps_x))
	print('Y grid steps = {}'.format(grid_steps_y))
	subprocess.run(['lamp', 'dome', '0'])  
	subprocess.run(['iitime', '60'])  	#in test 1, an integration time of 20 seconds gave peaks of ~7000 counts. Target 15,000 counts. Try integration time 40?
	subprocess.run(['icoadds', '1'])  
	#subprocess.run(['insamp', '4']) 		#readout mode
	print('(Set K rotator to 225?)')
	# subprocess.run(['modify','-s','ao','obtdname=' + 'open'])   #Set TRICK to open or hband, takes 60 seconds.
	# time.sleep(60) 
	# subprocess.run(['ifilt', 'kp', 'open'])     #Set filter. eg 'Drk' or 'kp open' 
	# time.sleep(10)
	make_log()
	log_entry('Filename','x','y','z','r','type')
	blockMoveNPEpics('to_pinhole_mask')
	blockMoveEpics(pcu_uz,99.32)
	for angle in position_angles:
		blockMoveEpics(pcu_r,65.7+angle)
		direction = 1
		for y in grid_steps_y:
			blockMoveEpics(pcu_y,y)	
			for x in grid_steps_x[::direction]:
				blockMoveEpics(pcu_x,x)	
				img_filename=take_image()
				log_entry(img_filename, pcu_x['read'].get(),pcu_y['read'].get(),pcu_uz['read'].get(),pcu_r['read'].get(),'')
			direction*=-1
	print('Finished taking images')

def blockMoveEpics(channel,position,):
	channel['write'].put(position)
	time.seep(1)
	while True:
		status = pcu_status.get()
		print('{} stage is at {} mm, status = {}'.format(channel['name'],channel['read'].get(),status))	
		if status == 'INPOS':
			print('Stage has reached position {}'.format(position))
			return
		elif status == 'FAULT':
			sys.exit('Stage has Faulted, exiting program.')
		time.sleep(2)

def blockMoveNPEpics(target):
	pcu_request.put(target)
	time.seep(1)
	while True:
		status = pcu_status.get()
		print('PCU position X = {}, Y = {}, Z = {}, Rot = {}, Status = {}'.format(pcu_x['read'].get(),pcu_y['read'].get(),pcu_uz['read'].get(),pcu_r['read'].get(),status))
		if status == 'INPOS':
			print('PCU has reached position {}'.format(target))
			return
		elif status == 'FAULT':
			sys.exit('Stage has Faulted, exiting program.')
		time.sleep(2)

#--------------------------------
main()
sys.exit(0)
#--------------------------------
