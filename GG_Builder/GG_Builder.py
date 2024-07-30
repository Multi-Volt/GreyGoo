import os
import re
import random
import trimesh
import numpy as np
import pandas as pd

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

# Global counters
BITCOUNTER = 0
TOTALLINECOUNTER = 0
LINECOUNTER = 0
MESHCOUNTER = 0

# Load the Excel file for command reference
try:
    PROGREFF = pd.ExcelFile("PROGREF.xlsx")
    REFDF = pd.read_excel(PROGREFF, sheet_name="Sheet1")
except FileNotFoundError:
    print("Can't Find PROGREF, skipping model generation.")
    REFDF = pd.DataFrame()

def lookup(command_name):
    """Lookup reference number for a command."""
    return REFDF.query(f"NAME == '{command_name}'")["REF"].values[0]

def p_lookup(command_name, letter):
    """Lookup parameter position for a command."""
    REFP = REFDF.query(f"NAME == '{command_name}'")
    REFP = REFP[REFP.isin([re.sub('[^a-zA-Z]', '', letter)])].dropna(axis=1, how='all').columns.tolist()[0]
    return int(re.sub('[^0-9]', '', REFP))

def generate_test_cases():
    """Prompt user to generate test cases."""
    while True:
        user_input = input("Would you like to generate test cases? (1 for Yes (Default), 0 for No): ").strip()
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

def count_files_in_directory(directory):
    """Count the number of files in a directory."""
    try:
        entries = os.listdir(directory)
        files = [entry for entry in entries if os.path.isfile(os.path.join(directory, entry))]
        return len(files)
    except FileNotFoundError:
        return "The directory does not exist."
    except Exception as e:
        return f"An error occurred: {e}"

def process_gcode_file():
    """Process the G-code file to create a minimal version."""
    gcode_file = input("Gcode Filename (no extension, defaults to TESTCOIN): ")

    if not gcode_file:
        gcode_file = "TESTCOIN"
    elif not os.path.isfile(f"{gcode_file}.gcode"):
        print("File does not exist or error in name, defaulting to TESTCOIN.")
        gcode_file = "TESTCOIN"

    minimal_gcode_file = f"{gcode_file}Minimal.gcode"
    
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

    return f"{gcode_file}Minimal"

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

def create_tooth(translation):
    """Create a tooth with translation and rotation."""
    cube = trimesh.creation.box(extents=[BIT_WIDTH, BIT_HEIGHT, BIT_LENGTH])
    rotation_angle = np.radians(BIT_ROTATION_ANGLE)  # 45 degrees

    # Define the rotation matrix for rotating around the Z-axis
    rotation_matrix = trimesh.transformations.rotation_matrix(
        angle=rotation_angle,
        direction=[0, 1, 0],  # Z-axis
        point=cube.centroid
    )
    cube.apply_transform(rotation_matrix)
    cube.apply_translation(translation)
    return cube

def mesh_reset():
    """Reset the mesh to the initial state."""
    mesh = trimesh.creation.box(extents=[189, 1.75, 222.75])
    mesh.apply_translation([189 / 2 - BIT_WIDTH / 2, -1.75 / 2, -222.75 / 2 + BIT_SPACING / 2])
    for i in range(90):
        for p in CHANNEL_OFFSETS:
            barrier = trimesh.creation.box(extents=[1.75, BIT_SPACING, 222.75])
            barrier.apply_translation([p, 0, -222.75 / 2 + BIT_SPACING / 2])
            mesh = trimesh.util.concatenate([mesh, barrier])
            mesh = trimesh.util.concatenate([mesh, create_tooth([0 - 1.75 / 2, -1.75 / 2, 0 - BIT_SPACING * i])])
            mesh = trimesh.util.concatenate([mesh, create_tooth([189 - 1.75 / 2, -1.75 / 2, 0 - BIT_SPACING * i])])
    return mesh

# Main
GCODEFILE = process_gcode_file()
print(f"GCODE file processed: {GCODEFILE} created")
TESTCASES = generate_test_cases()
SECTION_FOLDER = f"{GCODEFILE}_SECTIONS"
if not os.path.exists(SECTION_FOLDER):
    os.mkdir(SECTION_FOLDER)
print("Starting Build...")
with open(f"{GCODEFILE}.gcode", 'r+') as f1:
    TOTALLINES = sum(1 for _ in f1)
with open(f"{GCODEFILE}.gcode", 'r+') as f1:
    print(TOTALLINES)
    CURRENTMESH = mesh_reset()
    while TOTALLINECOUNTER < TOTALLINES:
        while LINECOUNTER < 90 and TOTALLINECOUNTER < TOTALLINES:
            CURRENTLINE = [word for word in f1.readline().strip().split() if word]
            print(CURRENTLINE)
            LINECOUNTER += 1
            TOTALLINECOUNTER += 1
            for x in format(lookup(CURRENTLINE[0]), '08b'):
                BITCOUNTER += 1
                if x == '1':
                    BIT = create_bit([CHANNEL_OFFSETS[0] + 1.75 * BITCOUNTER, 0, 0 - BIT_SPACING * (LINECOUNTER - 1)])
                    BIT.visual.vertex_colors = np.array([BIT_COLOR] * len(BIT.vertices))
                    CURRENTMESH = trimesh.util.concatenate([CURRENTMESH, BIT])
            BITCOUNTER = 0
            if len(CURRENTLINE) > 1:
                for x in range(1, len(CURRENTLINE)):
                    OSET = p_lookup(CURRENTLINE[0], CURRENTLINE[x])
                    if re.sub("[A-Z]", "", CURRENTLINE[x]) != '':
                        for i in str(bin(np.float16(re.sub("[A-Z]", "", CURRENTLINE[x])).view('H'))[2:].zfill(16)):
                            BITCOUNTER += 1
                            if i == '1':
                                BIT = create_bit([CHANNEL_OFFSETS[OSET] + 1.75 * BITCOUNTER, 0, 0 - BIT_SPACING * (LINECOUNTER - 1)])
                                BIT.visual.vertex_colors = np.array([BIT_COLOR] * len(BIT.vertices))
                                CURRENTMESH = trimesh.util.concatenate([CURRENTMESH, BIT])
                    else:
                        for i in range(16):
                            BITCOUNTER += 1
                            BIT = create_bit([CHANNEL_OFFSETS[OSET] + 1.75 * BITCOUNTER, 0, 0 - BIT_SPACING * (LINECOUNTER - 1)])
                            BIT.visual.vertex_colors = np.array([BIT_COLOR] * len(BIT.vertices))
                            CURRENTMESH = trimesh.util.concatenate([CURRENTMESH, BIT])
                    BITCOUNTER = 0
        CURRENTMESH.export(f"{SECTION_FOLDER}/{GCODEFILE}Section{MESHCOUNTER}.stl")
        MESHCOUNTER += 1
        CURRENTMESH = mesh_reset()
        LINECOUNTER = 0
print("3D Model generation complete.")
if TESTCASES:
    print("These sections were randomly selected to test:")
    print(generate_random_numbers(TEST_COUNT, 0, count_files_in_directory(SECTION_FOLDER)))

