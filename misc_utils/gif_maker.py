# -*- coding: utf-8 -*-
"""
Created on Fri Feb 15 13:45:51 2019

@author: disbr007
"""
import os
import imageio

def make_gif(prj_path, out_name, ext):
    images = []
    for file_name in os.listdir(prj_path):
        if file_name.endswith(ext):
            file_path = os.path.join(prj_path, file_name)
            images.append(imageio.imread(file_path))
            
    imageio.mimsave(os.path.join(prj_path, 'animated.gif'), images, duration=1.5)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("project_path", type=str, help='The directory containing images to combine')
	parser.add_argument("out_name", type=str, help='The name of the gif to be created')
	parser.add_argument("image_type", type=str, help="The format of the images to combine. E.g: 'png', 'jpg'.")
	args = parser.parse_args()
	make_gif(parser.project_path, parser.out_name, parser.image_type)

# project_path = r'C:\Users\disbr007\imagery\nga_maps\yearly'    
# make_gif(project_path, 'animated', '.png')