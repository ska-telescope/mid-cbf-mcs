#!/usr/bin/env python3
# script to generate Jones matrices in JSON

import sys, os, getopt
import json
from random import randint

def main(argv):
    json_file_path = ''
    json_file_name = ''
    try:
        opts, args = getopt.getopt(argv,'hp:n:',['help', 'path=','name='])
    except getopt.GetoptError:
        print('jones_matrix_gen.py -p <file path> -n <file name>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('jones_matrix_gen.py -p <file path> -n <file name>')
            sys.exit()
        elif opt in ('-p', '--path'):
            json_file_path = arg
            os.chdir(json_file_path)
        elif opt in ('-n', '--name'):
            json_file_name = arg

    jones_dict_list = []

    for number_of_tests in range(3): # number of receptor tests generated
        jones_details_list_receptor = []
        for number_of_receptors in range(2):
            receptor_details = []
            for fsid in range(2):
                jones_matrix = []
                for entry in range(16): # number of entries in Jones matrix; 16 = 4x4 matrix
                    jones_matrix.append(float(entry*(number_of_tests+1))) # fill the matrix with known data
                receptor_details.append({'fsid': randint(1, 26), 'matrix': jones_matrix})
            if number_of_receptors == 0:
                jones_details_list_receptor.append({'receptor': 1, 'receptorMatrix': receptor_details}) # number of receptor to be tested
            else:
                jones_details_list_receptor.append({'receptor': 4, 'receptorMatrix': receptor_details}) # number of receptor to be tested

        jones_dict_list.append({'matrixDetails': jones_details_list_receptor})

    #jones_matrix_file_name = json_file_path + json_file_name

    jones_dict = {'jonesMatrix': jones_dict_list}

    with open(json_file_name, 'w') as json_file:
        json.dump(jones_dict, json_file, indent=4, sort_keys=True)

if __name__ == "__main__":
   main(sys.argv[1:])