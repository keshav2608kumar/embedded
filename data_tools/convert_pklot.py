"""
Smart Parking Management System
Tool: PKLot Dataset Converter

Converts PKLot XML annotations (Center X, Center Y, Angle, Width, Height)
into standard YOLO format (Class, Center X, Center Y, Width, Height, normalized).
Class is always 0 (vehicle) as per project requirements.

STATUS: IMPLEMENTED
"""

import os
import glob
import xml.etree.ElementTree as ET
import argparse

def convert_pklot_to_yolo(xml_path, out_dir):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Extract image size if available or default (PKLot is typically 1280x720)
    width = 1280
    height = 720
    
    txt_filename = os.path.basename(xml_path).replace('.xml', '.txt')
    txt_path = os.path.join(out_dir, txt_filename)
    
    with open(txt_path, 'w') as f:
        for space in root.findall('space'):
            occupied = space.attrib.get('occupied', '0')
            if occupied == '1':
                # Vehicle is present
                center = space.find('contour/point') # Simplification: PKLot uses multiple points, 
                                                     # real implementation needs center of polygon
                
                rotated_rect = space.find('rotatedRect')
                if rotated_rect is not None:
                    cx = float(rotated_rect.find('center/x').text)
                    cy = float(rotated_rect.find('center/y').text)
                    w = float(rotated_rect.find('size/w').text)
                    h = float(rotated_rect.find('size/h').text)
                    
                    # Normalize for YOLO
                    nx = cx / width
                    ny = cy / height
                    nw = w / width
                    nh = h / height
                    
                    # class 0 = vehicle
                    f.write(f"0 {nx:.6f} {ny:.6f} {nw:.6f} {nh:.6f}\n")

def main():
    parser = argparse.ArgumentParser(description="Convert PKLot XML to YOLO")
    parser.add_argument('--input', type=str, required=True, help="Input directory containing PKLot XMLs")
    parser.add_argument('--output', type=str, required=True, help="Output directory for YOLO .txt files")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    xml_files = glob.glob(os.path.join(args.input, '**/*.xml'), recursive=True)
    
    print(f"Found {len(xml_files)} XML files.")
    count = 0
    for xml in xml_files:
        convert_pklot_to_yolo(xml, args.output)
        count += 1
        if count % 500 == 0:
            print(f"Processed {count}/{len(xml_files)} files...")
            
    print(f"Conversion complete. Output saved to {args.output}")

if __name__ == "__main__":
    main()
