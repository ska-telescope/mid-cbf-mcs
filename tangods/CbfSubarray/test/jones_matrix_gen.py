#!/usr/bin/env python3
# script to generate Jones matrices in JSON

import sys, os, getopt
import json
from random import choice, randint

def main(argv):
    json_file_path = ''
    json_file_name = ''
    num_tests = 0
    try:
        opts, args = getopt.getopt(argv,'hp:n:t:',['help', 'path=','name=', 'tests='])
    except getopt.GetoptError:
        print('jones_matrix_gen.py -p <file path> -n <file name> -t <number of tests>')
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
        elif opt in ('-t', '--tests'):
            num_tests = int(arg)

    jones_dict_list = []

    for number_of_tests in range(num_tests): # number of receptor tests generated
        length = choice([4, 16])
        jones_details_list_receptor = []
        for number_of_receptors in [1, 3]:
            receptor_details = []
            for fsid in range(1):
                jones_matrix = []
                for entry in range(length): # number of entries in Jones matrix; 16 = 4x4 matrix
                    jones_matrix.append(float(entry*(number_of_tests+1))) # fill the matrix with known data
                receptor_details.append({'fsid': 3, 'matrix': jones_matrix})
            jones_details_list_receptor.append({'receptor': number_of_receptors, 'receptorMatrix': receptor_details}) # number of receptor to be tested

        if length == 4:
            jones_dict_list.append({'destinationType': 'fsp', 'matrixDetails': jones_details_list_receptor})
        elif length == 16:
            jones_dict_list.append({'destinationType': 'vcc', 'matrixDetails': jones_details_list_receptor})

    jones_dict = {'jonesMatrix': jones_dict_list}

    with open(json_file_name, 'w') as json_file:
        json.dump(jones_dict, json_file, indent=4, sort_keys=True)

if __name__ == "__main__":
   main(sys.argv[1:])