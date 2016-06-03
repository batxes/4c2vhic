#!/usr/bin/python

import sys
import re
import ConfigParser
import pysam
from colour import Color
import heapq

number_of_arguments = len(sys.argv)
if number_of_arguments != 3: #Or all parameters, or no parameters 
    print "Not enought parameters. Model to be painted and config file are needed. You passed: ",sys.argv[1:]
    sys.exit()
if len(sys.argv) > 1:  #if we pass the arguments (in the cluster)
    model = sys.argv[1]
    ini_file = sys.argv[2]

#read the config file
config = ConfigParser.ConfigParser()
try:
    config.read(ini_file)
    verbose = int(config.get("ModelingValues", "verbose"))
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
    
    NFRAGMENTS = int(config.get("ModelingValues", "NFRAGMENTS"))
    NFRAGMENTS = int(NFRAGMENTS/WINDOW)
    
    number_of_models = int(config.get("ModelingValues", "number_of_models"))
    working_dir = config.get("ModelingValues", "working_dir")


    subset = int(config.get("AnalysisValues", "subset"))
    std_dev = int(config.get("AnalysisValues", "std_dev"))
    jump = number_of_models
    cut_off_percentage = int(config.get("AnalysisValues", "cut_off_percentage"))

    atac_path = config.get("Painting","Atac_path")
    color_low = config.get("Painting","Atac_color_low")
    color_high = config.get("Painting","Atac_color_high")
    
    
    
except:
    print "\nError reading the configuration file.\n"
    e = sys.exc_info()[1]
    print e
    sys.exit()


# create bed file
bamhandle = pysam.AlignmentFile(atac_path,"rb")
with open ("bed_file","w") as stdout:
    with open (files[0],"r") as stdin:
        for line in stdin:
            values = line.split("\t")
            read_count = bamhandle.count(values[0],int(values[1]),int(values[2])) #chrm, start, end
            stdout.write("{}\t{}\t{}\t{}\n".format(values[0],values[1],values[2],read_count))

#chr    from    to  value
bead_values = []
with open ("bed_file","r") as stdin:
    counter = 0
    added_reads = 0
    added_region = 0
    for line in stdin:
        values = line.split("\t")
        added_region += float(values[2])-float(values[1])
        added_reads += float(values[3])
        counter += 1
        if counter == WINDOW:
            counter = 0
            print added_reads, added_region
            normalized_read = added_reads/added_region
            print normalized_read
            print "---"
            bead_values.append(normalized_read)
            added_region = 0
            added_reads = 0
    if counter != WINDOW: #we add the min value to the last bead if it did not reach to Nfragments 
        normalized_read = added_reads/added_region
        bead_values.append(normalized_read)

# set color to beads
colorfrom = Color("#ffffff")
colorto = Color("#00ff00")
colors = list(colorfrom.range_to(colorto, NFRAGMENTS))

with open("coloring.cmd","w") as colored_model:
    colored_model.write("open {}\n".format(model))
    for number in range(NFRAGMENTS):
        smallest_value = heapq.nsmallest(number+1,bead_values)
        smallest_value = smallest_value[-1]
        position = bead_values.index(smallest_value)
        colored_model.write("color {} #{}\n".format(colors[number],position))






