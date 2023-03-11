# This script takes a series of images of the PCU with OSIRIS, for the purpose of distortion calibration.
# By Matthew Freeman 2023
# Using Avinash Surendran's blockMove functions

import numpy as np
import subprocess
import time
import sys
import ktl
import epics
import logging
from datetime import datetime

 #--------- Dither Pattern -------------
dither_spacing = 2.1 #mm
dither_grid_size = 5  #5x5 grid
position_angles =[0, 45]  #degrees
pinhole_x = 90  #x_stage location for the centre of the dither pattern
pinhole_y = 180
#--------------------------------------

#-------------Keck Keywords--------------
keck_kw = { 'ao':'ao1'
			'm1':'PCUM1POS',      #The same as x,y,z?
			'm2':'PCUM2POS',
			'm3':'PCUM3POS',
			'r':'PCUPR',
			'x':'PCUX',           #PCSFX
			'y':'PCUY',           #PCSFY
			'z':'PCUZ',           #PCSFLZ
			'state':'PCUSTATE'    #PCSFSTATE    #old? 
			'status':'PCUSTST'
			'r_status':'PCURSTST'  #may show the same as status? Check if needed when doing rotational blocking moves.
			'named_pos':'PCUNAME'  #PCSFNAME
			'pinhole':'to_pinhole_mask',		
			}
#----------------------------------------

#---------epics keywords---------------
pcu_status = epics.PV('k1:ao:pcu:stst')
pcu_request = epics.PV('k1:ao:pcu:request')
pcu_x = {'name':'x','write':epics.PV('k1:ao:pcu:M1Pos'),'read':epics.PV('k1:ao:pcu:M1Pos')}
pcu_y = {'name':'y','write':epics.PV('k1:ao:pcu:M2Pos'),'read':epics.PV('k1:ao:pcu:M2Pos')}
pcu_uz = {'name':'uz','write':epics.PV('k1:ao:pcu:M3Pos'),'read':epics.PV('k1:ao:pcu:M3Pos')}
pcu_r = {'name':'r','write':epics.PV('k1:ao:pcu:rot:pos'),'read':epics.PV('k1:ao:pcu:rot:pos Rb')}
#--------------------------------------

def main(mode = 'keck_keywords'):

	extent = (dither_grid_size-1) * dither_spacing /2
	grid_steps_x = np.linspace(pinhole_x-extent,pinhole_y+extent,dither_grid_size)
	grid_steps_y = np.linspace(pinhole_y-extent,pinhole_y+extent,dither_grid_size)

	subprocess.run(['lamp', 'dome', 1])  
	subprocess.run(['iitime', 20])  	#in test 1, an integration time of 20 seconds gave peaks of ~7000 counts. Target 15,000 counts. Try integration time 40?
	subprocess.run(['icoadds', 1])  
	subprocess.run(['insamp', 4]) 		#number of reads
	print('(Set K rotator to 225?)')

	# subprocess.run(['modify','-s','ao','obtdname=' + 'open'])   #Set TRICK to open or hband, takes 60 seconds.
	# time.sleep(60) 
	# subprocess.run(['ifilt', 'kp', 'open'])     #Set filter. eg 'Drk' or 'kp open' 
	# time.sleep(10)

	make_log()
	log_entry('Filename','x','y','z','r','type')

	if mode == 'epics':
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

	else:
		blockMoveNP(keck_kw['pinhole'])
		blockMove(keck_kw['m3'],99.32)
		for angle in position_angles:
			blockMove(keck_kw['r'],65.7 + angle)
			direction = 1
			for y in grid_steps_y:
				blockMove(keck_kw['m2'],y)	
				for x in grid_steps_x[::direction]:
					blockMove(keck_kw['m1'],x)	
					img_filename = take_image()
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

def blockMove(keyword, position):
	ktl.write(keck_kw['ao'], keyword, position)
	time.sleep(1)
	while True:
		pcu = ktl.read(keck_kw['ao'], keyword)
		status = ktl.read(keck_kw['ao'], keck_kw['status'])
		print(keyword +' is at ' + str(pcu) + ' mm and state is ' + status)
		if status == 'INPOS':
			print(keyword +' has reached designated position')
			return
		elif status == 'FAULT':
			sys.exit('Stage has FAULTED, exiting program..')
			time.sleep(2)

def blockMoveNP(target):
	ktl.write(keck_kw['ao'], keck_kw['named_pos'], target)
	time.sleep(1)
	while True:
		pcux = ktl.read(keck_kw['ao'], keck_kw['x'])
		pcuy = ktl.read(keck_kw['ao'], keck_kw['y'])
		pculz = ktl.read(keck_kw['ao'], keck_kw['z'])
		status = ktl.read(keck_kw['ao'], keck_kw['status'])
		print('PCUX = ' + pcux + ', PCUY = ' + pcuy + ', PCUZ = ' + pculz + ' and state is ' + status)
		if status == 'INPOS':
			print('Stage has reached designated position')
			return
		elif status == 'FAULT':
			sys.exit('Stage has FAULTED, exiting program..')
		time.sleep(2)

def take_image(n=1):
	subprocess.run(['igoi',n],check='True')
	filename = ktl.read('oids','lastfile')
	# filename = subprocess.run(['lastimage'],capture_output=True,text=True)
	return filename

def make_log():
	log_filename = datetime.now().strftime('PCU_%Y%m%d_%H%M%S.log')
	print('Log filename:', log_filename)
	logging.basicConfig(filename=log_filename, level=logging.INFO,format='%(message)s')

def log_entry(filename,x,y,z,r,flag):
	logging.info('{:>10} {:>10} {:>10} {:>10} {:>10} {:>10}'.format(filename,x,y,z,r,flag))

#--------------------------------
main('epics')
sys.exit(0)
#--------------------------------


