#!/usr/bin/python

# usage: python processor.py <data> <cfg> <weights>

import os
import argparse
import darknet
import records
import cameras
import multivator
import speed_ctrl


# need to declare global variables because they will be set for the first time inside a function

net = 0
meta = None

CURRENT = os.path.join(records.DIR, records.CURRENT + records.EXT)

def main():
	global CURRENT
	global net
	global meta
	if os.exists(os.path.join(records.DIR, CURRENT))
		raise ValueError('Processor is already running. If you did not start processor, delete the file %s and try again'%(CURRENT))
	meta = darknet.load_meta(b'/home/agbot/Yolo_mark_2/x64/Release/data/obj.data')
	net = darknet.load_net(b'/home/agbot/Yolo_mark_2/x64/Release/yolo-obj.cfg', b'/home/agbot/Yolo_mark_2/x64/Release/backup/yolo-obj_final.weights', 0)

if __name__ == '__main__':
	main()