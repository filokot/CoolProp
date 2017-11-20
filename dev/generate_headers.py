"""
In this module, we do some of the preparatory work that is needed to get
CoolProp ready to build.  This includes setting the correct versions in the 
headers, generating the fluid files, etc.
"""
from __future__ import division, print_function, unicode_literals
from datetime import datetime
import subprocess
import os
import sys
import json
import hashlib
import struct
import glob

json_options = {'indent' : 2, 'sort_keys' : True}

def get_hash(data):
    try:
        return hashlib.sha224(data).hexdigest()
    except TypeError:
        return hashlib.sha224(data.encode('ascii')).hexdigest()

# unicode
repo_root_path = os.path.normpath(os.path.join(os.path.abspath(__file__), '..', '..'))

# Load up the hashes of the data that will be written to each file
hashes_fname = os.path.join(repo_root_path,'dev','hashes.json')
if os.path.exists(hashes_fname):
    hashes = json.load(open(hashes_fname,'r'))
else:
    hashes = dict()

# 0: Input file path relative to dev folder
# 1: Output file path relative to include folder
# 2: Name of variable
#values = [
#    ('all_fluids.json','all_fluids_JSON.h','all_fluids_JSON'),
#    ('all_incompressibles.json','all_incompressibles_JSON.h','all_incompressibles_JSON'),
#    ('mixtures/mixture_departure_functions.json', 'mixture_departure_functions_JSON.h', 'mixture_departure_functions_JSON'),
#    ('mixtures/mixture_binary_pairs.json', 'mixture_binary_pairs_JSON.h', 'mixture_binary_pairs_JSON'),
#    ('mixtures/predefined_mixtures.json', 'predefined_mixtures_JSON.h', 'predefined_mixtures_JSON'),
#    ('cubics/all_cubic_fluids.json', 'all_cubics_JSON.h', 'all_cubics_JSON'),
#    ('cubics/cubic_fluids_schema.json', 'cubic_fluids_schema_JSON.h', 'cubic_fluids_schema_JSON')
#]
values = []
DEBUG = True
if (len(sys.argv) < 4):
    print("ERROR: {0} - Wrong number of arguments: {1}".format(__file__, len(sys.argv)))
    sys.exit(1)
else:
    if not os.path.isfile(sys.argv[1]): 
        print("ERROR: {0} - File not found: {1}".format(__file__, sys.argv[1]))
    values.append(tuple(sys.argv[1:4]))
    if (len(sys.argv) > 4):
        if str(sys.argv[4]) == "QUIET":
            DEBUG = False
        if str(sys.argv[4]) == "DEBUG":
            DEBUG = True
    

def TO_CPP(root_dir, hashes):
    def to_chunks(l, n):
        if n<1:
            n=1
        return [l[i:i+n] for i in range(0, len(l), n)]
    
    # Normalise path name
    root_dir = os.path.normpath(root_dir)
    
    # First we package up the JSON files
    combine_json(root_dir)
    
    for infile,outfile,variable in values:
        
        import json
        
        # Confirm that the JSON file can be loaded and doesn't have any formatting problems
        with open(os.path.join(root_dir,'dev',infile), 'r') as fp:
            try:
                jj = json.load(fp)
            except ValueError:
                file = os.path.join(root_dir,'dev',infile)
                print('"python -mjson.tool '+file+'" returns ->', end='')
                subprocess.call('python -mjson.tool '+file, shell = True)
                raise ValueError('unable to decode file %s' % file)
            
        json = open(os.path.join(root_dir,'dev',infile),'r').read().encode('ascii')

        # convert each character to hex and add a terminating NULL character to end the 
        # string, join into a comma separated string
        
        try:
            h = ["0x{:02x}".format(ord(b)) for b in json] + ['0x00']
        except TypeError:
            h = ["0x{:02x}".format(int(b)) for b in json] + ['0x00']
        
        # Break up the file into lines of 16 hex characters
        chunks = to_chunks(h, 16)
        
        # Put the lines back together again
        # The chunks are joined together with commas, and then EOL are used to join the rest
        hex_string = ',\n'.join([', '.join(chunk) for chunk in chunks])
            
        # Check if hash is up to date based on using variable as key
        if not os.path.isfile(os.path.join(root_dir,'include',outfile)) or variable not in hashes or (variable in hashes and hashes[variable] != get_hash(hex_string.encode('ascii'))):
        
            # Generate the output string
            output  = '// File generated by the script dev/generate_headers.py on '+ str(datetime.now()) + '\n\n'
            output += '// JSON file encoded in binary form\n'
            output += 'const unsigned char '+variable+'_binary[] = {\n' + hex_string + '\n};'+'\n\n'
            output += '// Combined into a single std::string \n'
            output += 'std::string {v:s}({v:s}_binary, {v:s}_binary + sizeof({v:s}_binary)/sizeof({v:s}_binary[0]));'.format(v = variable)
            
            # Write it to file
            f = open(os.path.join(root_dir,'include',outfile), 'w')
            f.write(output)
            f.close()
            
            # Store the hash of the data that was written to file (not including the header)
            hashes[variable] = get_hash(hex_string.encode('ascii'))
            
            if DEBUG: print(os.path.join(root_dir,'include',outfile)+ ' written to file')
        else:
            if DEBUG: print(outfile + ' is up to date')
        
def combine_json(root_dir):
    
    master = []
    
    for file in glob.glob(os.path.join(root_dir,'dev','fluids','*.json')):
        
        path, file_name = os.path.split(file)
        fluid_name = file_name.split('.')[0]
        
        try:
            # Load the fluid file
            fluid = json.load(open(file, 'r'))
        except ValueError:
            print('"python -mjson.tool '+file+'" returns ->', end='')
            subprocess.call('python -mjson.tool '+file, shell = True)
            raise ValueError('unable to decode file %s' % file)
        
        master += [fluid]

    fp = open(os.path.join(root_dir,'dev','all_fluids_verbose.json'),'w')
    fp.write(json.dumps(master, **json_options))
    fp.close()
    
    fp = open(os.path.join(root_dir,'dev','all_fluids.json'),'w')
    fp.write(json.dumps(master))
    fp.close()
    
    master = []
    
    for file in glob.glob(os.path.join(root_dir,'dev','incompressible_liquids','json','*.json')):
        
        path, file_name = os.path.split(file)
        fluid_name = file_name.split('.')[0]
        
        try:
            # Load the fluid file
            fluid = json.load(open(file, 'r'))
        except ValueError:
            print('"python -mjson.tool '+file+'" returns ->', end='')
            subprocess.call('python -mjson.tool '+file, shell = True)
            raise ValueError('unable to decode file %s' % file)
        
        master += [fluid]

    fp = open(os.path.join(root_dir,'dev','all_incompressibles_verbose.json'),'w')
    fp.write(json.dumps(master, **json_options))
    fp.close()
    
    fp = open(os.path.join(root_dir,'dev','all_incompressibles.json'),'w')
    fp.write(json.dumps(master))
    fp.close()        
    
def generate():
    
    #import shutil
    #shutil.copy2(os.path.join(repo_root_path, 'externals','Catch','single_include','catch.hpp'),os.path.join(repo_root_path,'include','catch.hpp'))
    #shutil.copy2(os.path.join(repo_root_path, 'externals','REFPROP-headers','REFPROP_lib.h'),os.path.join(repo_root_path,'include','REFPROP_lib.h'))
    
    TO_CPP(root_dir = repo_root_path, hashes = hashes)

    # Write the hashes to a hashes JSON file
    if hashes:
        fp = open(hashes_fname,'w')
        fp.write(json.dumps(hashes))
        fp.close()
        
if __name__=='__main__':
	generate()

