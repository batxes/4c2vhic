#!/usr/bin/python

# Script that runs small rounds of modeling with different Max distances

import sys, os, re, inspect
import getopt
import ConfigParser
import subprocess
from multiprocessing import Process, Lock, Pool, current_process
import argparse
import warnings
warnings.filterwarnings('ignore')
import time
from math import fabs
from random import randint
import IMP.kernel
import IMP.algebra
import IMP.core
import IMP.display
import IMP.base
import IMP.atom
import IMP.rmf
import IMP.container
import RMF
import numpy as np
from collections import defaultdict
import operator
import shutil
from os import listdir
from os.path import isfile, join

plot = True
try:
	import matplotlib
	matplotlib.use('Agg')
	import matplotlib.pylab as plt
except:
	plot = False
	print "\nPylab not installed. Skipping Zscore figures.\n"
	e = sys.exc_info()[1]
	print e
	
from math import fabs
from scipy.stats.stats import spearmanr

# realpath() will make your script run, even if you symlink it :)
cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile( inspect.currentframe() ))[0]))
if cmd_folder not in sys.path:
	sys.path.insert(0, cmd_folder)

# use this if you want to include modules from a subfolder
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"src")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)
    
from data_manager import fileCheck, sizeReader,  calculateNWindowedDistances, calculate_fragment_number

def worker(instructions):
    p = subprocess.Popen(instructions)
    p.wait()



def modeling((uZ, lZ, maxDis, starting_point, big_sampling)):
	
	y2 = maxDis
	if not big_sampling:
		number_of_models = pre_number_of_models
	else:
		number_of_models = total_number_of_models/number_of_cpus
	###################################### ###################################### 
	###################################### ###################################### 
	###################################### CHANGE DEPENDING ON MODELING VARIABLES
	
	rmf_video = False #If we wanna create a video of the IMP optimization
	evaluation = False #If we wanna evaluate the restraints 
	RESTRAINTS = [True,False,True,False] #4c counts, EV, HUB(connectivity), HLB(connectivity)
	RESTRAINTS_QUANTITY = [0,0,0,0]
	radius = 0

	k = 1
	if evaluation:
		std_dev = y2*0.2 #300 A #for evaluation #set a percentage of max distance. 20%
	#         std_dev = 1 #A 
	if rmf_video:
		frames = 5000
		
	#optimization variables
	LSTEPS = 5
	STEPS = 1
	NROUNDS= 10000 #10000 default

	endLoopCount = 0
	stopCount = 15
	endLoopValue = 0.00001
	hightemp = int (0.025 * NROUNDS )
	alpha = 1.0 * number_of_fragments #the weight of the fragments


	storage_folder = working_dir+"data/"+prefix+"/"+prefix+"_output_"+str(uZ)+"_"+str(lZ)+"_"+str(y2) #the dir where the data will be saved

	sampling = True
	score_file = storage_folder+"/score"+str(starting_point)+".txt"

	if os.path.exists(score_file): os.remove(score_file) 

	exv_values = []
	hub_values = []
																		# ZebraFish_output_1.0_-1.0_7000
	if not os.path.exists(storage_folder): os.makedirs(storage_folder)

	#radius_scale = 0.1 
	#radius_scale = 0.021695  #0.01 nm bp occupancy more or less.  #my value 0.04339. Davide = 0.005  #THIS ONE IS BAD

	radius_scale = 0.0423 #Radius of 1 bp in A. for the IrxB models. It's the canonical value for 30 nm chromatin

	# radius_scale = 0.00055 #depending my calculations
	## nucleosome = 200 bp. 30nm fiber -> 6-7 nucleosomes = 11 nm. -> then 1bp = 0.00846nm.
	## string of beads  11nm = 200bp. 1bp = 0.055nm. 
	## radius for both:
	##                30nm : 0.00423nm = 0.0423A
	##                string of beads : 0.0275nm = 0.275A
	#http://www.nature.com/nsmb/journal/v18/n1/pdf/nsmb.1936.pdf -> 0.01 occupancy
	#http://www.pnas.org/content/84/22/7802.full.pdf
	# dsDNA_1bp_size = 34 #Angstrom Double strand DNA 1 bp size
	####### FACT: 10 NUCLEOTIDES = 34 aNGSTROMS IN LENGTH



	#to get the size of the fragments, we read any file
	reads_size = sizeReader(fileCheck(files[0]))

	###################################### ###################################### 
	###################################### ###################################### 
	###################################### THE REAL DEAL!
	start_time = time.time()

	for sample in range(starting_point, starting_point+number_of_models):
		
		movers = []
		n_restraints = []
		genome = []
		spheres = []
		restraints = []
		movers = []
		bead_radii = []
		fragment_bp_quantity =[]
		scores = []
		
		chimera_file = prefix+str(sample)+".py"
		verboseprint ("Generating {} ...".format(chimera_file))
		values_file = prefix+str(sample)+".txt"
		w = IMP.display.ChimeraWriter(storage_folder+"/"+chimera_file)
		m = IMP.Model()
		
		if rmf_video:
			hierarqy= IMP.atom.Hierarchy.setup_particle(IMP.Particle(m))
		
		
		##########################    REPRESENTATION ##########################    REPRESENTATION
		##########################    REPRESENTATION ##########################    REPRESENTATION
		for i in range(number_of_fragments):
			
				# Create "untyped" Particles
				p = IMP.kernel.Particle(m,"particle_"+str(i))
				
				radius_sum = 0
				for j in range(int(fragments_in_each_bead)):
					radius_sum = radius_sum + reads_size[(i*int(fragments_in_each_bead))+j]
				radius = radius_scale * radius_sum #sphere radius proportional to fragments
				fragment_bp_quantity.append(radius_sum)
				verboseprint ("Fragment number:{} size:{} radius:{}".format(i,radius_sum,radius))
				#decorator with sphere  
				#Creating very far away particles (10000) could alter the final result of the beads that are not restrained
				d = IMP.core.XYZR.setup_particle(p, IMP.algebra.Sphere3D(IMP.algebra.Vector3D(randint(0,int(y2)), randint(0,int(y2)), randint(0,int(y2))), radius)) 
				bead_radii.append(radius)
				if i in(viewpoint_fragments):
					if i in(are_genes):
						color = IMP.display.Color(1,0.7,0)
					else: 
						color = IMP.display.Color(0,1,0)
					IMP.display.Colored.setup_particle(p, color)
				else:
					
	#               #one theme of color #blue, purple, red
					#color = IMP.display.Color(1/float(number_of_fragments)*i,0.0,1-1/float(number_of_fragments)*i) 
					
					
					#another them (only grey)
					color = IMP.display.Color(0.7,0.7,0.7) 
					
		
					
					IMP.display.Colored.setup_particle(p, color)
				
				d.set_coordinates_are_optimized(True) #tHIS IS FOR Ball Mover. BallMover can't move non-optimized attribute
				
				genome.append(p)
				spheres.append(d)
				# to use with montecarlo
				movers.append(IMP.core.BallMover([p], radius*2))
		#         movers[-1].set_was_used(True) -> #what does this do?
				
				if (rmf_video):
					IMP.atom.Mass.setup_particle(p,30)
					IMP.atom.Diffusion.setup_particle(p)
					hierarqy.add_child(IMP.atom.Hierarchy.setup_particle(p))
		##########################  RESTRAINTS ##########################  RESTRAINTS
		##########################  RESTRAINTS ##########################  RESTRAINTS
		
		#Distances
		#Excluded volume
		#Connectivity (HUB and HLB)
		#------------------
		
		r_count = 0
		reads_values,reads_weights,start_windows, end_windows = calculateNWindowedDistances(int(fragments_in_each_bead),uZ,lZ, y2,files)
		
		for j in range(len(files)):

			reads_weight = reads_weights[j]
			reads_value = reads_values[j]

			#get the number of reads and their size from our files
			f = fileCheck(files[j])
			reads_size = sizeReader(f)
			n_fragments = len(reads_size)/int(fragments_in_each_bead)  

	# # # # # # # # # # # # # # # # # # # # # # # # #harmonic restraints got from file
			counter = 0
			if (RESTRAINTS[0]):
				
				verboseprint ("LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOL")

				p1 = genome[viewpoint_fragments[j]]
				verboseprint ("LOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOL")
				for i in range(n_fragments):
					counter += 1
					if i != viewpoint_fragments[j]:
						if reads_value[i] != 0: #aplying the Z Score lower bound and upper bound (see calculate10WindowedDistances)
							if i not in ignore_beads:

								p2 = genome[i]
								
								#We add the diameters of the beads to the distance
								# the real distance is not from the core, we need to add the diameter, all the dna sequence
	#                         distance = bead_radii[j] + bead_radii[i] + float(reads_value[i])
								
								
								distance = float(reads_value[i])
								

								if distance != float(y2):
	#                             if True:
									#if distance < y2: #if maximum distance is reached, don't set a restraint, because it can be further in genomic distance
									kk2 = fabs(reads_weight[i])
									#if it is not in the window of the 4C interactome
									if (start_windows[j] > counter or end_windows[j] < counter):
										f = IMP.core.HarmonicLowerBound(distance, k*kk2)#don't give very good score?
										#f = IMP.core.Harmonic(distance, k*kk2)
										#harmonicLoweBound of max distance, so that they can not enter in a diameter of MAXDIS
									else:     
										f = IMP.core.Harmonic(distance, k*kk2) #)  #this is the harmonic score. I think second parameter is weight. it was 1.0 until now                  
				#                     f = IMP.core.Harmonic(float(reads_value[i]), k*fabs(reads_weight[i])) #)  #this is the harmonic score. I think second parameter is weight. it was 1.0 until now
									s = IMP.core.DistancePairScore(f)
									r = IMP.core.PairRestraint(s, (p1, p2))  #this is the restraint
									restraints.append(r)
									m.add_restraint(r)
									r_count += 1

				  
		n_restraints.append(r_count)  
		RESTRAINTS_QUANTITY[0] = r_count 
	# # # # # # # # # # # # # # # # # # # # # # # # # excluded volume
		if (RESTRAINTS[1]):
			mode = 1
			if mode == 1:
				r = IMP.core.ExcludedVolumeRestraint(genome,k) #we can remove k and 1 (genome,k,1) 
				restraints.append(r)
				m.add_restraint(r)
				  
			
			if mode == 2:
				# this container lists all pairs that are close at the time of evaluation
				nbl= IMP.container.ClosePairContainer(genome, 0,2)
				h= IMP.core.HarmonicLowerBound(300,1)
				sd= IMP.core.DistancePairScore(h)
				#sd= IMP.core.SphereDistancePairScore(h)
				# use the lower bound on the inter-sphere distance to push the spheres apart
				nbr= IMP.container.PairsRestraint(sd, nbl)
				m.add_restraint(nbr)
			RESTRAINTS_QUANTITY[1] = 1 
	# # # # # # # # # # # # # # # # # # # # # # # # # String of beads upper bound
		if (RESTRAINTS[2]):
			# using a HarmonicDistancePairScore for fixed length links is more
			# efficient than using a HarmonicSphereDistnacePairScore and works
			# better with the optimizer
			res_count = 0
			for i in range(len(genome)-1): 
					#### Different std_dev
				kk = 1    
				hub = IMP.core.HarmonicUpperBound(bead_radii[i]+bead_radii[i+1],k*kk) #como conseguir esto bien? 4 653 000
				p1 = genome[i]
				p2 = genome[i+1]
			#                 f = IMP.core.Harmonic(float(reads_value[i]), k * np.sqrt(reads_value[i]))  #this is the harmonic score. I think second parameter is weight. it was 1.0 until now
				s = IMP.core.DistancePairScore(hub)
				r = IMP.core.PairRestraint(s, (p1, p2))  #this is the restraint
				restraints.append(r)
				m.add_restraint(r)
				res_count += 1
			RESTRAINTS_QUANTITY[2] = res_count
		

	# # # # # # # # # # # # # # # # # # # # # # # # # String of beads lower bound 
		if (RESTRAINTS[3]): 
			res_count = 0 
			hlb = IMP.core.HarmonicLowerBound(300,k)
			for h in range(len(genome)):
				p1 = genome[h]
				for i in range(len(genome)):
					if i != h and i != h-1 and i != h+1:
						p2 = genome[i]
						s = IMP.core.DistancePairScore(hlb)
						r = IMP.core.PairRestraint(s, (p1, p2))  #this is the restraint
						restraints.append(r)
						m.add_restraint(r)  
						res_count+=1    
		##########################  SAMPLING ##########################  SAMPLING
		##########################  SAMPLING ##########################  SAMPLING
			RESTRAINTS_QUANTITY[3] = res_count
		
		cg = IMP.core.ConjugateGradients(m) 
		mc = IMP.core.MonteCarloWithLocalOptimization(cg, LSTEPS) 
		mc.set_return_best(True) 
		mc.set_name("MC")
		sm = IMP.core.SerialMover(movers)
		mc.add_mover(sm)
		 
		# sf = IMP.core.RestraintsScoringFunction(restraints, "RSF")
		# mc.set_scoring_function(sf) #monte carlo
		# cg.set_scoring_function(sf)     
		
		######################RMF VIDEO, INSTALL RMF AGAIN!! ######################    
		if rmf_video:
		 
		#create the RMF file to show the movie
			rmf= RMF.create_rmf_file('genome.rmf')
			rmf.set_description("Simulate genome.\n")
			 
			bd = IMP.atom.BrownianDynamics(m)
			bd.set_log_level(IMP.base.SILENT)
	#         bd.set_scoring_function(sf)

			bd.set_maximum_time_step(100)
			 
			IMP.rmf.add_hierarchy(rmf, hierarqy)
			IMP.rmf.add_restraints(rmf, restraints)

			oss= IMP.rmf.SaveOptimizerState(m,rmf)

			oss.update_always("initial conformation")
			oss.set_log_level(IMP.base.SILENT)
			oss.set_simulator(bd)
			bd.add_optimizer_state(oss)
			print "Optimizing twith Brownian Dynamics for the RMF file (movie)."
			bd.optimize(frames)
		
		IMP.base.set_log_level(IMP.base.SILENT)
		
		verboseprint( "Number of restraints: %i" % (len(restraints)))
		
		#first score
		scores.append(m.evaluate(False))
		verboseprint ("Start score: {}".format(scores[-1]))
		verboseprint ("\nStarts the optimization... ")

		#First hightemp iterations, do not stop the optimization
		verboseprint ("High temp iterations")
		for i in range(0,hightemp):
			temperature = alpha * (1.1 * NROUNDS - i) / NROUNDS
			mc.set_kt(temperature)
			scores.append(mc.optimize(STEPS))
			verboseprint ("{} {} temp:{}".format(i, scores[-1],mc.get_kt()))
		
		needed_time = time.time() - start_time
		lownrj = scores[-1]
		verboseprint ("Time for High temp iterations {}".format(needed_time))
		verboseprint ("Low temp iterations")
		for i in range(hightemp,NROUNDS): 
			temperature = alpha * (1.1 * NROUNDS - i) / NROUNDS
			mc.set_kt(temperature)
			scores.append(mc.optimize(STEPS))
			verboseprint ("{} {} temp:{}".format(i, scores[-1],mc.get_kt()))
			# Calculate the score variation and check if the optimization
			# can be stopped or not
			if lownrj > 0:
				deltaE = fabs((scores[-1] - lownrj) / lownrj)
			else:
				deltaE = scores[-1]
			if (deltaE < endLoopValue and endLoopCount == stopCount):
				break
			elif (deltaE < endLoopValue and endLoopCount < stopCount):
				endLoopCount += 1
				lownrj = scores[-1]
			else:
				endLoopCount = 0
				lownrj = scores[-1]
				
		
		

		suma1 = suma2 = suma3 = suma4 = 0
		if RESTRAINTS[0]:
			for r in restraints[0:RESTRAINTS_QUANTITY[0]]:
				suma1 = suma1 + r.evaluate(False)
	#         print RESTRAINTS_QUANTITY[0], "distance restraints: ",suma1
		if RESTRAINTS[1]:
			suma2 = restraints[RESTRAINTS_QUANTITY[0]].evaluate(False)
	#         print 1, " excluded Volume restraint: ",suma2
		if RESTRAINTS[2]:    
			n = RESTRAINTS_QUANTITY[0]+RESTRAINTS_QUANTITY[1]
			n2 = RESTRAINTS_QUANTITY[0]+RESTRAINTS_QUANTITY[1]+RESTRAINTS_QUANTITY[2]
			for r in restraints[n:n2]:
				suma3 = suma3 + r.evaluate(False)
	#         print n2-n, " connectivity HUB restraints: ",suma3
		if RESTRAINTS[3]:  
			n = RESTRAINTS_QUANTITY[0]+RESTRAINTS_QUANTITY[1]+RESTRAINTS_QUANTITY[2]
			n2 = RESTRAINTS_QUANTITY[0]+RESTRAINTS_QUANTITY[1]+RESTRAINTS_QUANTITY[2]+RESTRAINTS_QUANTITY[3]
			for r in restraints[n:n2]:
				suma4 = suma4 + r.evaluate(False)
	#         print n-n2, " connectivity HLB restraints: ",suma4
		verboseprint ("Total: ".format(suma1+suma2+suma3+suma4))
		verboseprint ("------------------------\n")
		verboseprint ("Number of restraints: %i" % (len(restraints)))
	#     if cg.set_stop_on_good_score(True):
	#         print "\n\ntermino con: "+str(i)
	#         break;
	#     if scoring_function.get_had_good_score():
	#         configuration_set.save()
	#     return configuration_set
		
		
		# print "\n\n############"
		# for r in restraints:
		#     print r.get_name(), r.evaluate(False)
		needed_time = time.time() - start_time
		verboseprint ("Time for Low temp iterations".format(needed_time))
		
		
		if (sampling):
			f1 = open (score_file,"a+")
			f1.write(str(sample)+"\t"+str(scores[-1])+"\n")
			f1.close()
		#EVALUATION
		if (evaluation):
		
			not_fulfilled = 0
			total_restraints = 0
			for i in range(len(files)):
				values = reads_values[i] 
				for j in range(n_fragments):
					if j != viewpoint_fragments[i]:
						# the distance is to the surface, not to the center, so add radius*2
						real_d = IMP.core.get_distance(spheres[j],spheres[viewpoint_fragments[i]]) 
		#                 real_d = real_d + radius*2
						real_d = real_d + bead_radii[j] + bead_radii[viewpoint_fragments[i]]
						
						should_be_d = values[j] #take out the Z score near 0 average values
						if should_be_d != 0:
							total_restraints += 1

							should_be_d = values[j] + bead_radii[j] + bead_radii[viewpoint_fragments[i]]
							if (should_be_d + std_dev < real_d  or should_be_d - std_dev > real_d):
								not_fulfilled += 1
					#             print "restraint "+str(j)+"not fulfilled"
	#                                 if (verbose == 3):
	#                                     print "Restraint " +str(j)+"-"+str(viewpoint_fragments[i])+" is "+str(real_d)+" and should be "+str(should_be_d)+" +- "+str(std_dev)+". Difference: "+str(should_be_d-real_d)
			verboseprint ("total: {}".format(total_restraints))
			verboseprint ("Not fulfilled restraints: {}/{} %{}".format(not_fulfilled,n_restraints[0],not_fulfilled*100/n_restraints[0]))


		# GENERATE THE TXT FILE WITH THE DATA
		f = open (storage_folder+"/"+values_file,"w")  
		for i in range(len(files)):
			for j in range(n_fragments):
				if j != viewpoint_fragments[i]:
					real_d = IMP.core.get_distance(spheres[j],spheres[viewpoint_fragments[i]]) 
					real_d = real_d + bead_radii[j] + bead_radii[viewpoint_fragments[i]]
					f.write(str(real_d)+"\t")
				else:
					f.write("0\t")
			f.write("\n")  
		f.close()
		
		for sphere in genome:
			g = IMP.core.XYZRGeometry(sphere)
			w.add_geometry(g)

		verboseprint ("\nModel number {}".format(sample))
		verboseprint ("Human Score: ".format(scores[-1]/1000000))
		exv_value = suma2/1000000
		exv_values.append(exv_value)
		verboseprint ("EXV: {}".format(exv_value))
		
		hub_value = suma3/1000000
		hub_values.append(hub_value)
		verboseprint ("HUB: {}".format(hub_value))
		needed_time = time.time() - start_time         
		verboseprint ("{} seconds.".format(needed_time))       

		verboseprint ("Mean exv for distance {} is: {}".format(y2,np.mean(exv_values))) 
		verboseprint ("Mean hub for distance {} is: {}".format(y2,np.mean(hub_values)))  
		verboseprint ("\nModel number {} finished.".format(sample))
	print "Modeling from {} to {} with variables {} {} {} finished".format(starting_point,starting_point+number_of_models,uZ,lZ,y2)
	 
def calculate_best_maxd():
		############# code that evaluates all the models with different distances and gives you which distance is the optimum


	#for each model (50 normally) we will get the length of the chromatin

	
	if not os.path.exists("{}data/{}".format(working_dir, prefix)):
		try:
			os.makedirs("{}data/{}".format(working_dir, prefix))
		except:
			print "\nError creating the data and {} directories.".format(prefix)
			e = sys.exc_info()[1]
			print e
			sys.exit()

	results_path = "{}data/{}/{}_best_maxd_results.txt".format(working_dir,prefix,prefix)
	aux_file = "get_genome_length.py"
	number_of_spheres = number_of_fragments - 1

	maxd_list = []
	size_list = []
	print "Calculating optimal max_dist parameter for the modeling...\n"
	with open (results_path,"w") as output_results:
		for maxd in np.arange(from_dist,to_dist+1,dist_bins):
			root = "{}data/{}/{}_output_0.1_-0.1_{}/".format(working_dir,prefix,prefix,maxd)
			all_distances = []
			for i in range(pre_number_of_models):
				###### we get the lengths of all models
				with open (aux_file,'w') as output:
					output.write("import os\nfrom chimera import runCommand as rc\nfrom chimera import replyobj\nos.chdir(\"{}\")\n".format(root))
					output.write("rc(\"open {}{}.py\")\n".format(prefix,i))
					for j in range (number_of_spheres):
						output.write("rc(\"distance #"+str(j)+" #"+str(j+1)+"\")\n")
				distance_output = subprocess.check_output(["chimera", "--nogui", aux_file])
				## reformat the output and read the distances
				#Distance between #297:1@ and #298:1@: 1131.491
				distance_sum = 0
				string = ""
				lista = []
				for line2 in distance_output:
					string = string + line2
					if line2 == "\n":
						lista.append(string)
						string = ""
				for line2 in lista:
					distance = re.search(r'Distance between',line2)
					if distance:
						distance = float(line2.split(' ')[5])
						distance_sum = distance_sum + distance
				#print ("model {} distance = {}").format(i,distance_sum)
				all_distances.append(distance_sum)
			#print all_distances
			size = np.mean(all_distances)
			#print "{}: {}".format(root,size)
			output_results.write("With max distance {}: {}A Equivalent to a genome of {} Mbp\n".format(maxd,size,size/0.0846/1000000)) #in Mbp
			maxd_list.append(maxd)
			size_list.append(size/0.0846/1000000)
			print "With max distance {}: {}A Equivalent to a genome of {} Mbp".format(maxd,size,size/0.0846/1000000)
	if os.path.isfile(aux_file):
		os.remove(aux_file)
		os.remove(aux_file+"c")

	print "Results writen in: {}".format(results_path)

	####calculate best maxd

	best_value = min(size_list, key=lambda x:abs(x-locus_size))
	best_maxd = maxd_list[size_list.index(best_value)]
 
	print "\nBest max distance for the modeling is: {}".format(best_maxd)
	return best_maxd

def calculate_heatdifference(path, n_files_inside,files,plot):        

    #FIRST CALCULATE OUR MODELS HEATMAP
    y2 = re.split('_',path)[-1] #I get 3000.0, now I take out .0 and convert to int
    y2 = int(re.split('\.',y2)[0])
    all_data = []
    number_of_reads = 0
    for i in range(n_files_inside):
        all_modified_arrays = []
        with open("{0}/{1}{2}.txt".format(path,prefix,i),"r") as f: #in 2.7 and newer versions I dont have to set indices

            #f = open(path+"/"+prefix+""+str(i)+".txt", "r")
            five_arrays = []
            for line in f:
                array = re.split('\t',line)
                reads = np.genfromtxt(array)
                five_arrays.append(reads)
                number_of_reads = len(reads)
                #the data is independent so get the values for each array in five_arrays
            for array in five_arrays:

                # Min distance = 0 value
                # Max distance = 100 value
                x1 = min(array)
                x2 = max(array)
                #y2 = 
                y1 = 300  
                slope = (y2-y1) / (x2-x1)
                array_modified = [slope*(read-x1)+y1 for read in array]

                all_modified_arrays.append(array_modified)
            all_data.append(all_modified_arrays)
       
    #calculate mean of all arrays
    mean_all_data = []
    # first we will calculate the mean for a gen_array, so we need to to this 5 times.
    for i in range(len(files)): #5 genes
        mean_one_gene_array = []
        for j in range(number_of_reads):
            value = 0
            for k in range(len(all_data)): #n_files_inside times
                current_array = all_data[k]
                value = value + current_array[i][j]
            mean = value/len(all_data)
            mean_one_gene_array.append(mean)
        mean_all_data.append(mean_one_gene_array)

    if plot:
        fig = plt.figure(figsize=(10,10))   
        ax = plt.subplot(2,1,2)
        z = np.array(mean_all_data)
        c = plt.pcolor(z,cmap=plt.cm.terrain_r)
        plt.colorbar()
        ax.set_yticks(np.arange(z.shape[1])+0.5, minor=False)
        plt.axis([0,z.shape[1],0,z.shape[0]])
        labels = [(x.split("/")[-1])[:15] for x in files]
        ax.set_yticklabels(labels)
        plt.xlabel("Beads")
    #     plt.xlabel("Genomic Position")

    #NOW CALCULATE THE 4C DATA'S HEATMAP (WITHOUT APLLYING LOG)
    HEAT_MAP_DATA, HEATMAP_DATA_LOG= calculateNWindowedDistances(fragments_in_each_bead,0,0,y2,files,False,True) #stored in HEATMAP_DATA_LOG
    
    heatmap_data_modified = []


    for array in HEAT_MAP_DATA:
    # without log
    # max reads = 0 distance
        x1 = max(array)
        x2 = min(array)
        y1 = 300  
        slope = (y2-y1) / (x2-x1)
        array_modified = [slope*(read-x1)+y1 for read in array]
        heatmap_data_modified.append(array_modified)
    if plot: 
        plt.title("Top: Raw data reads per bear. \nBottom: Average distance between beads of the models.")
        ax = plt.subplot(2,1,1)
        z = np.array(heatmap_data_modified)
        c = plt.pcolor(z,cmap=plt.cm.terrain_r)

        plt.colorbar()
        ax.set_yticks(np.arange(z.shape[1])+0.5, minor=False)
        plt.axis([0,z.shape[1],0,z.shape[0]])
        labels = [(x.split("/")[-1])[:15] for x in files]
        ax.set_yticklabels(labels)
        plt.subplots_adjust(bottom=0.1, right=0.999, top=0.9, left=0.2)
    #     plt.xlabel("Genomic Position")
        plt.savefig('{}_heatmap.png'.format(path))
        plt.close('all')


    #CALCULATE THE DIFFERENCE
    array2 = []
    for i in (mean_all_data):
        for j in i:
            array2.append(j)
    array1 = []
    for i in (heatmap_data_modified):
        for j in i:
            array1.append(j)

    #value = 0
    #for i in range(len(heatmap_data_modified)):
    #    for j in range(len(heatmap_data_modified[i])):
    #        # the difference will be relative
    #        # models with bigger MAX DIST are more likely to have bigger difference
    #        if mean_all_data[i][j] != 0.0:
    #            difference = fabs(mean_all_data[i][j]/y2-heatmap_data_modified[i][j]/y2)
    #            value = value + difference            
    #print "Value for "+path+" is: "+str(value)
    spearman_value = spearmanr(array1,array2)[0]
    print "Spearman correlation for {}: {}".format(path,str(spearman_value))

    #print "Spearman: "+str(spearmanr(heatmap_data_modified,mean_all_data))

    return spearman_value

def calculate_best_zscores():

	results_path = "{}data/{}/{}_heatmap_difference_results.txt".format(working_dir,prefix,prefix)
		   
	with open (results_path,"w") as output_results:
		all_scores = []
		best_uZ = 0
		best_lZ = 0
		best_score = 0.0
		for uZ in np.arange(from_zscore,to_zscore+zscore_bins,zscore_bins):
			for lZ in np.arange(-from_zscore, -to_zscore-zscore_bins, -zscore_bins):

				score = calculate_heatdifference(working_dir+"data/"+prefix+"/"+prefix+"_output_"+str(uZ)+"_"+str(lZ)+"_"+str(max_distance),pre_number_of_models,files,plot)
				output_results.write(str(uZ)+","+str(lZ)+","+str(max_distance)+"\t"+str(score)+"\n")
				all_scores.append(score)
				if score > best_score :
					best_uZ = uZ
					best_lZ = lZ
					best_score = score
		#output_results.write("MIN: {}".format(min(all_scores)))   
		output_results.write("Max: {}".format(max(all_scores)))   
		#print min(all_scores)

	print "Best uZ: {}, Best lZ: {}".format(best_uZ,best_lZ)
	if plot:
		print "\nFigures comparing raw data vs modeling were created in {}data/{}/".format(working_dir,prefix)
    
	return best_uZ,best_lZ

def run_analysis(std_dev,cut_off_percentage):
	
	jump = total_number_of_models / number_of_cpus
	std_dev = std_dev
	cut_off_percentage = cut_off_percentage
	root = "{}data/{}/{}_output_{}_{}_{}/".format(working_dir,prefix,prefix,uZ,lZ,max_distance)
	score_file = "{}/score.txt".format(root)


	pyfiles = [ f for f in listdir(root) if isfile(join(root,f)) and f.endswith(".py") ]
	number_of_models = len(pyfiles)
	try:
		os.remove(root+"score.txt")
	except OSError:
		pass
	scorefiles = [ f for f in listdir(root) if isfile(join(root,f)) and f.startswith("score") ]
	number_of_score_files = len(scorefiles)

	models = defaultdict(list) # dict: each model ahs a list of 2 values

	# first we create a unified score.txt
	with open (score_file,"w") as f:
		counter = 0
		for i in range(number_of_score_files):
			with open (root+"score"+str(counter)+".txt", "r") as f2:
				for line in f2:
					f.write(line)
			counter = counter + jump
			
	# create the dictionary and populate it
	with open (score_file, "r") as f:
		counter = 0
		for line in f:
			counter += 1
			model = []
			values = re.split("\t", line)
			number = int(values[0])
			score = float(values[1])
			model.append(score)
			models[number] = model
			if counter == number_of_models:
				break

	# models = models[:number_of_models]    #take aonly the first ones 
			
	reads_values,reads_weights,start_windows, end_windows = calculateNWindowedDistances(int(fragments_in_each_bead),uZ,lZ, max_distance,files)


	print "getting best {} models".format(subset)
	analized_models = 0
	ok_models = 0
	for i in range(number_of_models):
		distances_in_model = []
		with open (root+prefix+str(i)+".txt","r") as f:
			for line in f:
				value = re.split("\t",line)
				distances_in_model.append(value)
	#         print distances_in_model
		#EVALUATION
	 
	 
		not_fulfilled = 0
		total = 0
		for k in range(len(files)):

			values = reads_values[k] 
			for j in range(number_of_fragments):
				if j != viewpoint_fragments[k]:
					
					real_d = distances_in_model[k][j]
					 
					should_be_d = values[j] 
					if should_be_d != 0:
						total += 1
						if (should_be_d + std_dev < float(real_d)  or should_be_d - std_dev > float(real_d)):
							not_fulfilled += 1
				#             print "restraint "+str(j)+"not fulfilled"
							
							verboseprint ("Restraint " +str(j)+"-"+str(viewpoint_fragments[k])+" is "+str(real_d)+" and should be "+str(should_be_d)+" +- "+str(std_dev)+". Difference: "+str(should_be_d-float(real_d)))
		#print str(i)+"-> Not fulfilled restraints: "+str(not_fulfilled)+"/"+str(total),"%",str(not_fulfilled*100/(total))     
		fulfil_percentage = not_fulfilled*100/total
		verboseprint( "not_fulfilled -> {} out of {} restraints: {}% of all restraints are not fulfilled in this model.".format(not_fulfilled,total,fulfil_percentage))
		if fulfil_percentage <= cut_off_percentage:
			models[i].append(not_fulfilled)
			ok_models += 1
		else:
			try:
				del models[i]
			except:
				print "Not enough models for the analysis. Try changing the parameters in the config file for 'std_dev' or 'cut_off_percentage'."
		analized_models += 1
		verboseprint ("Percentage of models that fulfill the threshold: {}%".format(100*ok_models/analized_models))
		verboseprint ("{}/{}".format(ok_models,analized_models))
		#print "{} -> number of models in subset {}".format(i,len(models))  
		#after poplating all and takign out the models out of the cout off, take the subset of models



	#order the dictionary by score
	sorted_models = sorted(models.items(), key=operator.itemgetter(1))
	print "Number of models below cutoff: {}".format(len(sorted_models))

	# store them in a folder
	storage_folder = working_dir+"data/"+prefix+"/"+prefix+"_final_output_"+str(uZ)+"_"+str(lZ)+"_"+str(max_distance)+"/" #the dir where the data will be saved
	print "copying best {} models to {} ...".format(subset,storage_folder)
	if not os.path.exists(storage_folder): os.makedirs(storage_folder)   

	try: 
		models_subset = sorted_models [:subset]
		for k in range(subset):
			i = models_subset[k][0]
			shutil.copyfile("{}{}{}.py".format(root,prefix,i), "{}{}{}.py".format(storage_folder,prefix,i) )
			shutil.copyfile("{}{}{}.txt".format(root,prefix,i), "{}{}{}.txt".format(storage_folder,prefix,i) )
	except:
		print "\n !!!! Can not get {} models. Seek less models or relax the std_dev and cut_off_percentage.\n ".format(subset)
		return False,std_dev,cut_off_percentage



	# create the file to open in chimera
	# superposition of the best models
	with open(working_dir+"data/"+prefix+"_superposition.py","w") as f:
		f.write("import os\nfrom chimera import runCommand as rc\nfrom chimera import replyobj\nos.chdir(\""+root+"\")\n")
		f.write("rc(\"open {}{}.py\")\n".format(prefix,models_subset[0][0]))
		for k in range(1,subset):
			i = models_subset[k][0]
	#         print("rc(\"open {}{}.py\")\n".format(prefix,i))
	#         print("rc(\"match #{}-{} #0-{}\")\n".format((k+1)*number_of_fragments,(k+1)*number_of_fragments+number_of_fragments-1,number_of_fragments-1))
			f.write("rc(\"open {}{}.py\")\n".format(prefix,i))
			f.write("rc(\"match #{}-{} #0-{}\")\n".format(k*number_of_fragments,k*number_of_fragments+number_of_fragments-1,number_of_fragments-1))

	print "Superposition of {} models created in {}data/{}\n".format(subset,working_dir,prefix)


	return True,std_dev,cut_off_percentage

########################################## MAIN ##########################################

working_dir = (os.path.realpath(__file__)).split("/")[:-1]
working_dir = "/".join(working_dir)+"/"

parser = argparse.ArgumentParser(
description=''' Modeling process.''',
epilog= """ Simple usage: python run_genome_maxd.py .""")
parser.add_argument("--cpu",type=int, default=1, action="store", dest="number_of_cpus",help='number of CPUs that will be used in this script')
parser.add_argument("--preNmodels",type=int, default=50, action="store", dest="pre_number_of_models",help='number of models that will be generated in the pre-modeling phase')
parser.add_argument("--Nmodels",type=int, default=50000, action="store", dest="number_of_models",help='number of models that will be generated in the modeling phase')
parser.add_argument("--from_dist",type=int, default=5000, action="store", dest="from_dist",help='minimum max-distance that will be used in the pre-modeling phase')
parser.add_argument("--to_dist",type=int, default=12000, action="store", dest="to_dist",help='maximum max-distance that will be used in the pre-modeling phase')
parser.add_argument("--dist_bins",type=int, default=1000, action="store", dest="dist_bins",help='size of jump between from_dist and to_dist')
parser.add_argument("--from_zscore",type=float, default=0.1, action="store", dest="from_zscore",help='minimum Z-score that will be used in the pre-modeling phase')
parser.add_argument("--to_zscore",type=float, default=1.2, action="store", dest="to_zscore",help='maximum Z-score that will be used in the pre-modeling phase')
parser.add_argument("--zscore_bins",type=float, default=0.1, action="store", dest="zscore_bins",help='size of jump between from_zscore and to_zscore')
parser.add_argument("--verbose", action="store_true", dest="verbose",help='Verbose True for more information while executing the script')
parser.add_argument("data_dir", action="store",help='location of the 4C data. primers.txt needs tobe in there also')
parser.add_argument("--working_dir", action="store",default=working_dir, dest="working_dir",help='location where the models will be generated')
parser.add_argument("--subset",type=int, action="store",default=200, dest="subset",help='Number of best models out of the Modeling process')
parser.add_argument("--std_dev", type=int,action="store",default=0, dest="std_dev",help='Standard deviation of the distances between beads, to be considered fulfilled')
parser.add_argument("--cut_off_percentage",type=int, action="store",default=15, dest="cut_off_percentage",help='Percetange of fulfilled distances in each model to be a good model')
parser.add_argument("prefix", action="store",help='Name of the models')
parser.add_argument("--fragments_in_each_bead", default=0, dest="fragments_in_each_bead" ,action="store",help='Number of fragments that will be represented with each bead')

args = parser.parse_args()
print args	

number_of_cpus = args.number_of_cpus
pre_number_of_models = args.pre_number_of_models
total_number_of_models = args.number_of_models
from_dist = args.from_dist
to_dist = args.to_dist
dist_bins = args.dist_bins
from_zscore = args.from_zscore
to_zscore = args.to_zscore
zscore_bins = args.zscore_bins
verbose = args.verbose
data_dir = args.data_dir
working_dir = args.working_dir
prefix = args.prefix
fragments_in_each_bead = args.fragments_in_each_bead
max_distance = 0 #updated in calculate_best_maxd()
uZ = 0 #updated in calculate_best_zscores
lZ = 0 #updated in calculate_best_zscores
subset = args.subset
std_dev = args.std_dev
cut_off_percentage = args.cut_off_percentage

ignore_beads = "NO"
if ignore_beads != "NO":
	ignore_beads = re.sub('[\n\s\t]','',ignore_beads)
	ignore_beads = ignore_beads.split(",")
	ignore_beads = [ int(i) for i in ignore_beads]
else:
	ignore_beads = [] #empty
	
	
if verbose:
	def verboseprint(text):
		print text;
else:   
	verboseprint = lambda *a: None      # do-nothing function


# get the name and position from primers.txt
#primers.txt:  name chrN:position
primers = {}
viewpoint_positions = []
primers_file = fileCheck(data_dir+"primers.txt")
for line in primers_file:
	m = re.search('([^\s\t]+).*chr\w+:(\d+)', line)
	try:
		primers[m.group(1)] = int(m.group(2))
	except:
		break
print "This is what primers.txt has: "
for k,v in primers.iteritems():
	print "Viewpoint:{}  position:{}".format(k,v)
for k,v in primers.iteritems():
	viewpoint_positions.append(v)
file_names = primers.keys()
files = [data_dir+f for f in file_names]

# read one of the files and get number of fragments and default fragments_in_each_bead
# a_4c_file: chrN start end value
start_frag = 0
end_frag = 0
number_of_fragments = 0

a_4c_file = fileCheck(data_dir+primers.keys()[0])
for line in a_4c_file:
	values = line.split()
	if len(values) != 4:
		continue
	if start_frag != 0:
		start_frag = int(values[1])
	end_frag = int(values[2])
	number_of_fragments += 1

locus_size = end_frag - start_frag
viewpoint_fragments = calculate_fragment_number(viewpoint_positions,files[0])


#default, we want 100 beads in each model
if fragments_in_each_bead == 0:
	fragments_in_each_bead = int(number_of_fragments / 100)
	
viewpoint_fragments = [int(i/fragments_in_each_bead) for i in viewpoint_fragments]
are_genes = viewpoint_fragments

# now get number of beads
number_of_fragments = int(number_of_fragments/fragments_in_each_bead)

p = Pool(number_of_cpus)

execute = []

#pre-modeling maxD
print "Pre-modeling Started"
for dist in range(from_dist,to_dist+dist_bins,dist_bins):
	instructions = (0.1 ,-0.1, dist,0 ,False)
	execute.append(instructions)
p.map(modeling,execute)
execute = []


#max distance calculation
print "Now calculate maxD"
max_distance = calculate_best_maxd()
print "maxD calculated"

#pre-modeling Zscores
for zmax in np.arange(from_zscore,to_zscore+zscore_bins,zscore_bins):
	for zmin in np.arange(-from_zscore, -to_zscore-zscore_bins, -zscore_bins):
		instructions = (zmax, zmin, max_distance, 0 ,False)
		execute.append(instructions)
p.map(modeling,execute)
execute = []
print "Pre-modeling finished"

#z_scores calculation
print "Now calculate best uz and lz"
uZ, lZ = calculate_best_zscores()
print "uz and lz calculated"

#Modeling Zscores
print "Modeling started"
number_of_models = total_number_of_models/number_of_cpus
for cpu in range(number_of_cpus):
	instructions = ( uZ,lZ, max_distance, cpu*number_of_models ,True)
	execute.append(instructions)
p.map(modeling,execute)
execute = []
print "Modeling finished"

#Analysis of models
print "Analysis started"
if std_dev == 0:
	std_dev = max_distance / 10  

increase_dev_or_cutoff = 0
while True:
	print "Running Analysis with:"
	print "Std_dev: {}".format(std_dev)
	print "cut_off_percentage: {}".format(cut_off_percentage)
	fulfilled, std_dev, cut_off_percentage = run_analysis(std_dev,cut_off_percentage)
	if fulfilled:
		break
	else:
		if increase_dev_or_cutoff == 0:
			std_dev = std_dev + max_distance*0.02 #increase std_def
			increase_dev_or_cutoff = 1
		else:
			cut_off_percentage = cut_off_percentage+2 #increase #cut_off
			increase_dev_or_cutoff = 0			
print "Final analysis thresholds: "
print "Std_dev: {}".format(std_dev)
print "cut_off_percentage: {}".format(cut_off_percentage)