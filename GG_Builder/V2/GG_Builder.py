import os
import re
import random
import trimesh
import numpy as np
import pandas as pd
import multiprocessing as mp
import time

# Constants and settings
BIT_HEIGHT = 1.75  # Height of the bits
BIT_WIDTH = 1.75   # Width of each bit
BIT_LENGTH = 1.75  # Length of each bit
BIT_SPACING = 2.475  # Spacing between each bit
BIT_ROTATION_ANGLE = 45  # Rotation angle for each bit in degrees
CHANNEL_OFFSETS = [ # Offsets for all the channel guides
    10.5, 9 * BIT_WIDTH + 10.5, 26 * BIT_WIDTH + 10.5,
    43 * BIT_WIDTH + 10.5, 61 * BIT_WIDTH + 10.5,
    78 * BIT_WIDTH + 10.5, 95 * BIT_WIDTH + 10.5
]
TEST_COUNT = 8 # Amount of test case numbers to generate
BIT_COLOR = [125, 0, 0, 255]  # Color of the bits (RGBA)
line_lists = []
section_nums = []
test_sections = []

# Load the Excel file for command reference
try:
    PROG_REF = pd.ExcelFile("PROGREF.xlsx")
    REF_DF = pd.read_excel(PROG_REF, sheet_name="Sheet1")
except FileNotFoundError:
    print("Can't Find PROGREF, skipping model generation.")
    REF_DF = pd.DataFrame()

def lookup(line):
    """Lookup reference number for a command in PROG_REF."""
    cmd = REF_DF.query(f"NAME == '{line[0]}'")
    cmd = cmd.values.tolist()
    params = []
    cmd_num = 0
    for i in range (1, len(line)):
        params.append(re.sub('[^a-zA-Z]', '', line[i]))
    for p in cmd:
        if set(params).issubset(p):
            cmd_num = p[0]
            break
    return cmd_num

def p_lookup(command_name, letter):
    """Lookup parameter position for a command in PROG_REF."""
    REF_PARAM = REF_DF.query(f"NAME == '{command_name}'")
    REF_PARAM = REF_PARAM[REF_PARAM.isin([re.sub('[^a-zA-Z]', '', letter)])].dropna(axis=1, how='all').columns.tolist()[0]
    return int(re.sub('[^0-9]', '', REF_PARAM))

def generate_test_cases():
    """Prompt user to generate test cases."""
    while True:
        user_input = input("Would you like to generate test cases? (1 for Yes (Default), 0 for No): ").strip()
        if re.fullmatch(r'[01]', user_input):
            return bool(int(user_input))
        else:
            print("Invalid input. Defaulting to Yes (1).")
            return True
            
def show_lines():
    """Prompt user to show current lines."""
    while True:
        user_input = input("Would you like to show the current line being processed? (1 for Yes, 0 for No (Default)): ").strip()
        if re.fullmatch(r'[01]', user_input):
            return bool(int(user_input))
        else:
            print("Invalid input. Defaulting to No (0).")
            return False
            
def arrange_models():
    """Prompt user to arrange models into a print in place model."""
    while True:
        user_input = input("Would you like the builder to create a print in place model? (1 for Yes (Default), 0 for No): ").strip()
        if re.fullmatch(r'[01]', user_input):
            return bool(int(user_input))
        else:
            print("Invalid input. Defaulting to Yes (1).")
            return True

def generate_random_numbers(count, start, end):
    """Generate a list of unique random numbers."""
    if count > (end - start + 1):
        raise ValueError("Count is greater than the range of unique numbers available.")
    return random.sample(range(start, end + 1), count)


def process_gcode_file():
    """Process the G-code file to create a minimal version."""
    gcode_file = input("Gcode Filename (no extension, defaults to TESTCOIN): ")

    if not gcode_file:
        gcode_file = "TESTCOIN"
    elif not os.path.isfile(f"{gcode_file}.gcode"):
        print("File does not exist or error in name, defaulting to TESTCOIN.")
        gcode_file = "TESTCOIN"

    minimal_gcode_file = f"{gcode_file}_minimal.gcode"
    
    if not os.path.isfile(minimal_gcode_file):
        try:
            with open(f"{gcode_file}.gcode", 'r') as f1, open(minimal_gcode_file, 'w') as o:
                for FLINE in f1:
                    if FLINE[0] not in "; \n":
                        o.write(FLINE.split(';')[0].strip() + "\n")
        except IOError as e:
            print(f"An error occurred while processing the file: {e}")
    else:
        print("File already exists, skipping...")

    return f"{gcode_file}_minimal"

def create_bit(translation):
    """Create a bit with translation and rotation."""
    cube = trimesh.creation.box(extents=[BIT_WIDTH, BIT_HEIGHT, BIT_LENGTH])
    rotation_angle = np.radians(BIT_ROTATION_ANGLE)  # 45 degrees

    # Define the rotation matrix for rotating around the Z-axis
    rotation_matrix = trimesh.transformations.rotation_matrix(
        angle=rotation_angle,
        direction=[1, 0, 0],  # Z-axis
        point=cube.centroid
    )
    cube.apply_transform(rotation_matrix)
    cube.apply_translation(translation)
    return cube

def mesh_reset():
    """Reset the mesh to the initial state."""
    return trimesh.load("GG_GearedBase_fixed.stl")

# Main
GCODE_FILE = process_gcode_file()
print(f"GCODE file processed: {GCODE_FILE} created")
test_cases = generate_test_cases()
show_lines_bool = show_lines()
print_in_place = arrange_models()
SECTION_FOLDER = f"{GCODE_FILE}_SECTIONS"
if not os.path.exists(SECTION_FOLDER):
    os.mkdir(SECTION_FOLDER)
if not os.path.exists(f"{GCODE_FILE}_TESTCASES") and test_cases:
    os.mkdir(f"{GCODE_FILE}_TESTCASES")
with open(f"{GCODE_FILE}.gcode", 'r') as f1:
    f1.seek(0, 0)
    GCODE = f1.read()
    GCODE = GCODE.split('\n')
    GCODE = list(filter(None, GCODE))
    total_lines = len(GCODE)
    print(f"{GCODE_FILE}.gcode has {total_lines} lines to process...")
    f1.close()
print("Starting Build...")

    
if test_cases:
    print("These sections were randomly selected to test:")
    test_sections = generate_random_numbers(TEST_COUNT, 0, int(total_lines/90))
    print(test_sections)

def build_section(lines):
    bit_counter = 0
    start_time = time.perf_counter()
    current_mesh = mesh_reset()
    temp_lines = []
    mesh_num = lines[2]
    if not os.path.exists(f"{SECTION_FOLDER}/{GCODE_FILE}Section{mesh_num}.stl"):
        print(f"Section {mesh_num} starting...")
        for index in range(lines[0],lines[1]):
            current_line = [word for word in GCODE[index].strip().split() if word]
            if mesh_num in test_sections:
                temp_lines.append(GCODE[index] + '\n')
            if show_lines_bool:
                print(current_line)
            for x in format(lookup(current_line), '08b'):
                bit_counter += 1
                if x == '1':
                    bit = create_bit([CHANNEL_OFFSETS[0] + 1.75 * bit_counter, 0, 0 - BIT_SPACING * (((index+1)-lines[0]) - 1)])
                    bit.visual.vertex_colors = np.array([BIT_COLOR] * len(bit.vertices))
                    current_mesh = trimesh.util.concatenate([current_mesh, bit])
            bit_counter = 0
            if len(current_line) > 1:
                for x in range(1, len(current_line)):
                    OSET = p_lookup(current_line[0], current_line[x])
                    if re.sub("[A-Z]", "", current_line[x]) != '':
                        for i in str(bin(np.float16(re.sub("[A-Z]", "", current_line[x])).view('H'))[2:].zfill(16)):
                            bit_counter += 1
                            if i == '1':
                                bit = create_bit([CHANNEL_OFFSETS[OSET] + 1.75 * bit_counter, 0, 0 - BIT_SPACING * (((index+1)-lines[0]) - 1)])
                                bit.visual.vertex_colors = np.array([BIT_COLOR] * len(bit.vertices))
                                current_mesh = trimesh.util.concatenate([current_mesh, bit])
                    else:
                        for i in range(16):
                            bit_counter += 1
                            bit = create_bit([CHANNEL_OFFSETS[OSET] + 1.75 * bit_counter, 0, 0 - BIT_SPACING * (((index+1)-lines[0]) - 1)])
                            bit.visual.vertex_colors = np.array([BIT_COLOR] * len(bit.vertices))
                            current_mesh = trimesh.util.concatenate([current_mesh, bit])
                    bit_counter = 0
        current_mesh.export(f"{SECTION_FOLDER}/{GCODE_FILE}Section{mesh_num}.stl")
        print(f"Section {mesh_num} completed in {time.perf_counter()-start_time}(s)")
    else:
        print(f"Section {mesh_num} already exists, skipping...")
    if mesh_num in test_sections and not os.path.exists(f"{GCODE_FILE}_TESTCASES/Case{mesh_num}.txt"):
        with open(f"{GCODE_FILE}_TESTCASES/Case{mesh_num}.txt", 'w+') as o:
            o.writelines(temp_lines)
            o.close()

build_start = time.perf_counter()
if __name__ == '__main__' and not REF_DF.empty:
    print("Trying to multiprocess...")
    pool = mp.Pool()
    for i in range(0,int(total_lines/90)+1):
        if (90*i + 90) > total_lines:
            line_lists.append([90*i, total_lines, i])
        else:
            line_lists.append([90*i, 90*i+90, i])
    pool.map(build_section, line_lists)
    
if print_in_place:
    mesh = trimesh.Trimesh()
    for i in range(0,int(total_lines/90)+1):
        mesh = trimesh.util.concatenate([mesh, trimesh.load(f"{SECTION_FOLDER}/{GCODE_FILE}Section{i}.stl").apply_translation([0,(1.75+0.2)*int(total_lines/90)-(1.75+0.2)*i,0])])
    rotation_angle = np.radians(90)  # 90 degrees
    # Define the rotation matrix for rotating around the Z-axis
    rotation_matrix = trimesh.transformations.rotation_matrix(
        angle=rotation_angle,
        direction=[1, 0, 0],  # Z-axis
        point=mesh.centroid
    )
    mesh.apply_transform(rotation_matrix)
    mesh.export(f"{GCODE_FILE}_PIP.stl")
print(lookup([word for word in GCODE[4].strip().split() if word]))
print(f"Build Completed! Total time to build: {time.perf_counter() - build_start}(s).")
