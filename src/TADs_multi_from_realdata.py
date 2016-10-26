#!/usr/bin/python

# Script modified from Tads_multi to take data from real hi-c's in this format:
# 0,0,12312
# 0,1,111
# 0,2,1132
# ...
#and generates the heatmap

## CREATE THE CMD TO USE IN CHIMERA
import re
import os
import sys
import subprocess
from multiprocessing import Pool
from itertools import combinations, chain
import time
import ConfigParser
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def chimera_worker(chimera_file):
    distance_output = subprocess.check_output(["chimera", "--nogui", chimera_file])
    return distance_output

calculate_the_matrix = True #to get only the HIC from the text use TADS_generate_matrix

number_of_arguments = len(sys.argv)
if number_of_arguments != 3: #Or all parameters, or no parameters 
    print "Not enought parameters. Config file, matrix file (absolute path) are required. You passed: ",sys.argv[1:]
    sys.exit()
if len(sys.argv) > 1:  #if we pass the arguments (in the cluster)
    ini_file = sys.argv[1]
    root = sys.argv[2]
    matrix_path = sys.argv[2]
    root = matrix_path.split("/")[0:-1]
    root = '/'.join(root)
    root = root+"/"
    print root
    
#read the config file
config = ConfigParser.ConfigParser()
try:
    config.read(ini_file)
    
    prefix = config.get("ModelingValues", "prefix")
    verbose = int(config.get("ModelingValues", "verbose"))
    WINDOW = float(config.get("ModelingValues", "WINDOW"))
    
    viewpoints = config.get("TADs", "viewpoints")
    viewpoints = re.sub('[\n\s\t]','',viewpoints)
    viewpoints = viewpoints.split(",")
    viewpoints = [ int(i) for i in viewpoints]
    viewpoints = [int(i/WINDOW) for i in viewpoints]
    
    genes = config.get("ModelingValues", "genes")
    genes = re.sub('[\n\s\t]','',genes)
    genes = genes.split(",")
    genes = [ int(i) for i in genes]
    genes = [int(i/WINDOW) for i in genes]
    
    
    number_of_models = int(config.get("ModelingValues", "number_of_models"))
    
    gene_names = config.get("TADs", "gene_names")
    gene_names = re.sub('[\n\s\t]','',gene_names)
    gene_names = gene_names.split(",")
    color = config.get("TADs", "color")
    color = re.sub('[\n\s\t]','',color)
    color = color.split(",")
    color = [ int(i) for i in color]
    
    number_of_cpu = int(config.get("TADs", "number_of_cpu"))
    maximum_hic_value= int(config.get("TADs", "maximum_hic_value"))

except:
    print "\nError reading the configuration file.\n"
    e = sys.exc_info()[1]
    print e
    sys.exit()
distance_file = "get_genome_distance_{}".format(prefix)
path = "{}distances_of_current_model_{}".format(root,prefix)
start_time = time.time()

NFRAGMENTS = 0
with open(matrix_path, 'r') as std_in:
    for line in std_in:
        values = line.split(",") 
        NFRAGMENTS = int(values[0])

NFRAGMENTS += 1
with open(matrix_path, 'r') as std_in:
    matrix_mean = np.zeros((NFRAGMENTS,NFRAGMENTS))
    for line in std_in:
        values = line.split(",")
        print values
        matrix_mean[int(values[0])][int(values[1])] = float(values[2])

max_list = []
for line in matrix_mean:
    max_list.append(max(line))

if verbose==3:  print "Generating matrix to plot..."     
#matrix_mean = matrix_mean[15:-15,15:-15]
#viewpoints = [x-15 for x in viewpoints]
fig = plt.figure()
ax = plt.subplot(1,1,1)
z = np.array(matrix_mean)



vmax = max(max_list)
c = plt.pcolor(z,cmap=plt.cm.PuRd,vmax=vmax, vmin=0)
ax.set_frame_on(False)
plt.colorbar()


#to set the viewpoints
#plt.scatter(viewpoints, viewpoints, s=20, c=color,cmap=plt.cm.autumn)

#ax.set_yticks(viewpoints)
#ax.set_xticks(viewpoints)
#ax.set_xticklabels(gene_names, minor=False)
#ax.set_yticklabels(gene_names, minor=False)
#plt.tick_params(axis='both', which='major', labelsize=8)
#plt.xticks(rotation=90)

plt.axis([0,z.shape[1],0,z.shape[0]])

fig.set_facecolor('white')
#plt.show()

pp = PdfPages('{}{}_HiC.pdf'.format(root,prefix))
pp.savefig(fig)
pp.close()
print '{}_HiC.pdf writen'.format(prefix)
print "{} segundos".format(time.time() - start_time)
#Distance between #1 marker 1  and #10 marker 1 : 2203.213
            