import os
import configparser
import copy
from pathlib import Path

def parse_pp3(file_path):
    """Parse .pp3 file and extract Temperature, Green (Tint), and Exposure Compensation"""
    config = configparser.ConfigParser()
    config.read(file_path, encoding='utf-8')

    # Extract values from [White Balance] and [Exposure] sections
    temp = config.getint('White Balance', 'Temperature')
    green = config.getfloat('White Balance', 'Green')  # This is "Tint"
    compensation = config.getfloat('Exposure', 'Compensation')

    return config, temp, green, compensation

def create_pp3(config, temp, green, compensation, output_path):
    """Create new .pp3 file with interpolated values"""
    # Update the specific values in their correct sections
    config.set('White Balance', 'Temperature', str(int(temp)))
    config.set('White Balance', 'Green', f"{green:.3f}")
    config.set('Exposure', 'Compensation', f"{compensation:.3f}")

    # Write the config back to file
    with open(output_path, 'w', encoding='utf-8') as f:
        config.write(f)

def interpolate_values(start_val, end_val, current_step, total_steps):
    """Linear interpolation between two values"""
    return start_val + (end_val - start_val) * (current_step / total_steps)

def process_timelapse(directory):
    """Main processing function"""
    # Get sorted NEF and PP3 files
    nef_files = sorted([f for f in os.listdir(directory) if f.endswith('.NEF')])
    pp3_files = sorted([f for f in os.listdir(directory) if f.endswith('.pp3')])

    # Create mapping of NEF basenames to their indices
    nef_basenames = [os.path.splitext(f)[0] for f in nef_files]  # e.g., "0001"

    # Find keyframes (existing .pp3 files)
    keyframes = []
    for pp3_file in pp3_files:
        # pp3_file is like "0001.NEF.pp3", we need "0001"
        if pp3_file.endswith('.NEF.pp3'):
            basename = pp3_file[:-8]  # Remove ".NEF.pp3"
            if basename in nef_basenames:
                index = nef_basenames.index(basename)
                config, temp, green, compensation = parse_pp3(os.path.join(directory, pp3_file))
                keyframes.append({
                    'index': index,
                    'basename': basename,
                    'temp': temp,
                    'green': green,
                    'compensation': compensation
