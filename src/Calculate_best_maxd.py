#!/usr/bin/python

import re
import os
import sys
import subprocess
import numpy as np
import ConfigParser
sys.path.insert(1,'/home/bioinfo/workspace/genome/utils')
#for each model (500 normally) we will get the length of the chromatin 

number_of_arguments = len(sys.argv)
if number_of_arguments != 4 and number_of_arguments != 1: #Or all parameters, or no parameters 
    print "Not enought parameters. start_dist, end_dist, dist_bins number_of_models and config file are required. You passed: ",sys.argv[1:]
    sys.exit()
if len(sys.argv) > 1:  #if we pass the arguments (in the cluster)
    start_dist = float(sys.argv[1])
    end_dist = float(sys.argv[2])
    dist_bins = float(sys.argv[3])
    number_of_models = float(sys.argv[4])
    ini_file = sys.argv[5]
else: #if no arguments, set the default values
    start_dist = 6000.0 #upper bound Z-score
    end_dist = 6000.0 #lower bound Z-score 
    dist_bins = 1000.0  # Max distance BETWEEN bead
    number_of_models = 50
    ini_file = "config.ini"
#read the config file
config = ConfigParser.ConfigParser()
try:
    config.read(ini_file)
    
    prefix = config.get("ModelingValues", "prefix")
    
    WINDOW = float(config.get("ModelingValues", "WINDOW"))
    
    files = config.get("ModelingValues", "files")
    files = re.sub('[\n\s\t]','',files)
    files = files.split(",")    
    
    viewpoints = config.get("ModelingValues", "viewpoints")
    viewpoints = re.sub('[\n\s\t]','',viewpoints)
    viewpoints = viewpoints.split(",")
    viewpoints = [ int(i) for i in viewpoints]
    viewpoints = [int(round(i/WINDOW)) for i in viewpoints]
    
    genes = config.get("ModelingValues", "genes")
    genes = re.sub('[\n\s\t]','',genes)
    genes = genes.split(",")
    genes = [ int(i) for i in genes]
    genes = [int(round(i/WINDOW)) for i in genes]
    
    NFRAGMENTS = int(config.get("ModelingValues", "NFRAGMENTS"))
    NFRAGMENTS = int(NFRAGMENTS/WINDOW)
    
    number_of_models = int(config.get("ModelingValues", "number_of_models"))
    
    working_dir = config.get("ModelingValues", "working_dir")
except:
    print "\nError reading the configuration file.\n"
    e = sys.exc_info()[1]
    print e
    sys.exit()
    
results_path = "../data/{}_best_maxd_results.txt".format(prefix)
aux_file = "get_genome_length.py"
number_of_spheres = NFRAGMENTS - 1

print "!! NOTE !! remember that we need models with 0.1 and -0.1 of uZ and lZ for the best calculation."
with open (results_path,"w") as output_results:
    for maxd in np.arange(start_dist,end_dist+1,dist_bins):
        root = "{}data/{}_output_0.1_-0.1_{}/".format(working_dir,prefix,maxd)
        all_distances = []
        for i in range(number_of_models):
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
        output_results.write("With max distance {}: {}A Equivalent to a genome of {} Mbp".format(maxd,size,size/0.0846/1000000)) #in Mbp
if os.path.isfile(aux_file):
    os.remove(aux_file) 
    os.remove(aux_file+"c")   
  
    
 


         


            

