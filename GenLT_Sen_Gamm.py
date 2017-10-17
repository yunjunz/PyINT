#! /usr/bin/env python
#################################################################
###  This program is part of PyINT  v1.0                      ### 
###  Copy Right (c): 2017, Yunmeng Cao                        ###  
###  Author: Yunmeng Cao                                      ###                                                          
###  Email : ymcmrs@gmail.com                                 ###
###  Univ. : Central South University & University of Miami   ###   
#################################################################

import numpy as np
import os
import sys  
import subprocess
import getopt
import time
import glob
import argparse

def check_variable_name(path):
    s=path.split("/")[0]
    if len(s)>0 and s[0]=="$":
        p0=os.getenv(s[1:])
        path=path.replace(path.split("/")[0],p0)
    return path

def read_template(File, delimiter='='):
    '''Reads the template file into a python dictionary structure.
    Input : string, full path to the template file
    Output: dictionary, pysar template content
    Example:
        tmpl = read_template(KyushuT424F610_640AlosA.template)
        tmpl = read_template(R1_54014_ST5_L0_F898.000.pi, ':')
    '''
    template_dict = {}
    for line in open(File):
        line = line.strip()
        c = [i.strip() for i in line.split(delimiter, 1)]  #split on the 1st occurrence of delimiter
        if len(c) < 2 or line.startswith('%') or line.startswith('#'):
            next #ignore commented lines or those without variables
        else:
            atrName  = c[0]
            atrValue = str.replace(c[1],'\n','').split("#")[0].strip()
            atrValue = check_variable_name(atrValue)
            template_dict[atrName] = atrValue
    return template_dict


def ras2jpg(input, strTitle):
    call_str = "convert " + input + ".ras " + input + ".jpg"
    os.system(call_str)
    call_str = "convert " + input + ".jpg -resize 250 " + input + ".thumb.jpg"
    os.system(call_str)
    call_str = "convert " + input + ".jpg -resize 500 " + input + ".bthumb.jpg"
    os.system(call_str)
    call_str = "$INT_SCR/addtitle2jpg.pl " + input + ".thumb.jpg 14 " + strTitle
    os.system(call_str)
    call_str = "$INT_SCR/addtitle2jpg.pl " + input + ".bthumb.jpg 24 " + strTitle
    os.system(call_str)

def UseGamma(inFile, task, keyword):
    if task == "read":
        f = open(inFile, "r")
        while 1:
            line = f.readline()
            if not line: break
            if line.count(keyword) == 1:
                strtemp = line.split(":")
                value = strtemp[1].strip()
                return value
        print "Keyword " + keyword + " doesn't exist in " + inFile
        f.close()

def usage():
    print '''
******************************************************************************************************
 
                 Estimating the offsets of two SAR images based on cross-correlation.

   usage:
   
            GenOff_Gamma.py ProjectName Mdate Sdate workDir
      
      e.g.  GenOff_Gamma.py PacayaT163TsxHhA 131021 131101 /Yunmeng/SCRATCH
      
*******************************************************************************************************
    '''   
    
def main(argv):
    
    if len(sys.argv)>=4:
        projectName = sys.argv[1]
        Mdate = sys.argv[2]
        Sdate = sys.argv[3]
        if len(sys.argv)==5:
            workDir = sys.argv[4]
        else:
            workDir = os.getcwd()
    else:
        usage();sys.exit(1)
    

      
    scratchDir = os.getenv('SCRATCHDIR')
    templateDir = os.getenv('TEMPLATEDIR')
    templateFile = templateDir + "/" + projectName + ".template"
    
    processDir = scratchDir + '/' + projectName + "/PROCESS"
    slcDir     = scratchDir + '/' + projectName + "/SLC"


    INF = 'IFG'
    if INF=='IFG' or INF =='IFGRAM':
        Suffix=['']
    elif INF=='MAI':
        Suffix=['.F','.B']
    elif INF=='RSI':
        Suffix=['.HF','.LF']
    else:
        print "The folder name %s cannot be identified !" % igramDir
        usage();sys.exit(1)

#################################  Define coregistration parameters ##########################
    templateContents=read_template(templateFile)
    
    if 'Coreg_Coarse'          in templateContents: coregCoarse = templateContents['Coreg_Coarse']                
    else: coregCoarse = 'both' 

    if 'thresh4cor'          in templateContents: thresh4cor = templateContents['thresh4cor']                
    else: thresh4cor = ' - '  
        
    if 'rwin4cor'          in templateContents: rwin4cor = templateContents['rwin4cor']                
    else: rwin4cor = '256'  
    if 'azwin4cor'          in templateContents: azwin4cor = templateContents['azwin4cor']                
    else: azwin4cor = '256'      
    if 'rsample4cor'          in templateContents: rsample4cor = templateContents['rsample4cor']                
    else: rsample4cor = '16'  
    if 'azsample4cor'          in templateContents: azsample4cor = templateContents['azsample4cor']                
    else: azsample4cor = '32'  
        
    if ' rpos4cor'          in templateContents:  rpos4cor = templateContents[' rpos4cor']                
    else:  rpos4cor = ' - '  
    if 'azpos4cor'          in templateContents: azpos4cor = templateContents['azpos4cor']                
    else: azpos4cor = ' - '  
        

        
    if 'rfwin4cor'          in templateContents: rfwin4cor = templateContents['rfwin4cor']                
    else: rfwin4cor = str(int(int(rwin4cor)/2))
    if 'azfwin4cor'          in templateContents: azfwin4cor = templateContents['azfwin4cor']                
    else: azfwin4cor = str(int(int(azwin4cor)/2))  
    if 'rfsample4cor'          in templateContents: rfsample4cor = templateContents['rfsample4cor']                
    else: rfsample4cor = str(2*int(rsample4cor))  
    if 'azfsample4cor'          in templateContents: azfsample4cor = templateContents['azfsample4cor']                
    else: azfsample4cor = str(2*int(azsample4cor))  
        

    
    rlks = templateContents['Range_Looks']
    azlks = templateContents['Azimuth_Looks']
    
# input slcs

    SslcDir = slcDir + "/" + Sdate
    MslcDir = slcDir + "/" + Mdate

    MslcImg = MslcDir + "/" + Mdate + ".slc"
    MslcPar = MslcDir + "/" + Mdate + ".slc.par"
    SslcImg = SslcDir + "/" + Sdate + ".slc"
    SslcPar = SslcDir + "/" + Sdate + ".slc.par"

# output slcs

    MrslcImg = workDir + "/" + Mdate + ".rslc"
    MrslcPar = workDir + "/" + Mdate + ".rslc.par"
    SrslcImg = workDir + "/" + Sdate + ".rslc"
    SrslcPar = workDir + "/" + Sdate + ".rslc.par"
    Srslc0Img = workDir + "/" + Sdate + ".rslc0"
    Srslc0Par = workDir + "/" + Sdate + ".rslc0.par"
    
# output multi-looked amplitude

    MamprlksImg = workDir + "/" + Mdate + "_" + rlks+"rlks.amp"	
    MamprlksPar = workDir + "/" + Mdate + "_" + rlks+"rlks.amp.par"
    SamprlksImg = workDir + "/" + Sdate + "_" + rlks+"rlks.amp"
    SamprlksPar = workDir + "/" + Sdate + "_" + rlks+"rlks.amp.par"
    OFFSTD = workDir + "/" + Mdate + '-' + Sdate +".off_std"	
    
    simDir = scratchDir + '/' + projectName  + "/SIM" 
    simDir = simDir + '/sim_' + Mdate

    HGTSIM      = simDir + '/sim_' + Mdate + '_' + rlks+'rlks.rdc.dem'
    
    if not os.path.isfile(HGTSIM):
        call_str= "Generate_RdcDEM_Gamma.py  " + projectName + ' ' + Mdate
        os.system(call_str)

    lt0 = workDir + "/lt0" 
    lt1 = workDir + "/" + Mdate + '.lt'
    STD= workDir + "/" + Mdate + '.lt_std'
    mli0 = workDir + "/mli0" 
    diff0 = workDir + "/diff0" 
    offs0 = workDir + "/offs0"
    snr0 = workDir + "/snr0"
    offsets0 = workDir + "/offsets0"
    coffs0 = workDir + "/coffs0"
    coffsets0 = workDir + "/coffsets0"
    off = workDir + "/" + Mdate + "-" + Sdate + ".off"
    offs = workDir + "/offs"
    snr = workDir + "/snr"
    offsets = workDir + "/offsets"
    coffs = workDir + "/coffs"
    coffsets = workDir + "/coffsets"

    if os.path.isfile(diff0):
        os.remove(diff0)
    if os.path.isfile(off):
        os.remove(off)

# real processing

    call_str = "$GAMMA_BIN/multi_look " + MslcImg + " " + MslcPar + " " + MamprlksImg + " " + MamprlksPar + " " + rlks + " " + azlks
    os.system(call_str)

    call_str = "$GAMMA_BIN/multi_look " + SslcImg + " " + SslcPar + " " + SamprlksImg + " " + SamprlksPar + " " + rlks + " " + azlks
    os.system(call_str)

    
    call_str = "$GAMMA_BIN/rdc_trans " + MamprlksPar + " " + HGTSIM + " " + SamprlksPar + " " + lt0
    os.system(call_str)

    width_Mamp = UseGamma(MamprlksPar, 'read', 'range_samples')
    width_Samp = UseGamma(SamprlksPar, 'read', 'range_samples')
    line_Samp = UseGamma(SamprlksPar, 'read', 'azimuth_lines')

    call_str = "$GAMMA_BIN/geocode " + lt0 + " " + MamprlksImg + " " + width_Mamp + " " + mli0 + " " + width_Samp + " " + line_Samp + " 2 0"
    os.system(call_str)

    call_str = "$GAMMA_BIN/create_diff_par " + SamprlksPar + " - " + diff0 + " 1 0"
    os.system(call_str)

    call_str = "$GAMMA_BIN/init_offsetm " + mli0 + " " + SamprlksImg + " " + diff0 + " 2 2 - - - - - 512"
    os.system(call_str)

    call_str = "$GAMMA_BIN/offset_pwrm " + mli0 + " " + SamprlksImg + " " + diff0 + " " + offs0 + " " + snr0 + " " + rwin4cor + " " + azwin4cor + " " + offsets0 + " 2 " + rsample4cor + " " + azsample4cor
    os.system(call_str)
  
    call_str = "$GAMMA_BIN/offset_fitm " + offs0 + " " + snr0 + " " + diff0 + " " + coffs0 + " " + coffsets0 + " - 3"
    os.system(call_str)
    
    call_str = "$GAMMA_BIN/offset_pwrm " + mli0 + " " + SamprlksImg + " " + diff0 + " " + offs0 + " " + snr0 + " " + rfwin4cor + " " + azfwin4cor + " " + offsets0 + " 2 " + rfsample4cor + " " + azfsample4cor
    os.system(call_str)
  
    call_str = "$GAMMA_BIN/offset_fitm " + offs0 + " " + snr0 + " " + diff0 + " " + coffs0 + " " + coffsets0 + " - 4 >" + STD
    os.system(call_str)

    
    
    call_str = "$GAMMA_BIN/gc_map_fine " + lt0 + " " + width_Mamp + " " + diff0 + " " + lt1
    os.system(call_str)
    


    os.remove(lt0)
    os.remove(mli0)
    os.remove(diff0)
    os.remove(offs0)
    os.remove(snr0)
    os.remove(offsets0)
    os.remove(coffs0)
    os.remove(coffsets0)
 

    print "Generate lookup table for resampling is done!"
 
    sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[:])
