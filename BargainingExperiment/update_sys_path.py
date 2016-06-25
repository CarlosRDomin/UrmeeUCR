'''
This script fixes the following problem. When run_server.py is executed, sys.path is initialized to contain its parent
folder (BargainingExperiment). This means that when we try to import any modules from the package BargainingExperiment,
Python throws an ImportError exception.

Instead, we need BargainingExperiment's parent folder to be included in sys.path, such that package BargainingExperiment
can be found and imported.
'''

import sys
import os


current_file_abspath = os.path.abspath(__file__)  # Get the absolute path to the current file
parent_folder = os.path.dirname(current_file_abspath)  # Get the path to this script's parent folder (should be BargainingExperiment's path)
grandpa_folder = os.path.dirname(parent_folder)  # Get the path to BargainingExperiment's parent folder. This is what needs to be included in sys.path
sys.path.insert(0, grandpa_folder)  # Prepend BargainingExperiment's parent directory to sys.path
