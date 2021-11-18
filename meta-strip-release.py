from PIL import Image
from PIL.ExifTags import TAGS
import csv
import os
from glob import glob

'''
Function pseudocode:
1. Read images from a directory
2. Extract exif/metadata and write to a csv
3. Save a copy of image without having the metadata associated to it
'''

def meta_strip(path_to_images):
    '''
    path_to_images: Should be a windows dir path and contain all images at the same level. This function does not traverse heirarchical directories
    Example-C:\projects\meta-strip\inputdata
    '''

    img_dir= os.listdir(path_to_images)
    out_path = os.path.join(path_to_images,'stripped-data')
    
    #Create an output folder
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    #Traverse through the input dir and read images one by one    
    for f in img_dir:
        with Image.open(path_to_images+"\\" + f) as img:
            exif_dict = img._getexif()
            exif = {}
            for k,v in exif_dict.items():
                #Tags.get gives the corresponding tag name for the tag number
                #For eg: MAKE tag has 271 number
                exif[TAGS.get(k)]=v 
            
            
            del exif['MakerNote']

            narray = [i for i in range(len(exif)+1)]
            for i in range(len(exif)+1):
                narray[i]=' '
            narray[0]=f
            print('Processed file '+narray[0])

            #Create an EXIF.csv to store the image exif data. This will be stored in folder 'stripped-data'
            with open(os.path.join(out_path,'EXIF.csv'),newline='', encoding='utf-8',mode='a') as csv_file:
                writer = csv.writer(csv_file)
                for i,(key,value) in enumerate(exif.items()):
                    writer.writerow([narray[i],key, value])
                writer.writerow([' ',' ',' '])
                
                
        # Saves EXIF stripped copy of image
        image = Image.open(path_to_images+"\\"+f)
        image_clean = Image.new(image.mode, image.size)
        image_clean.putdata(list(image.getdata()))
        
        #This s to rectify the rotation caused when saving PIL image 
        im_flipped = image_clean.transpose(method=Image.ROTATE_270) #PIL loses metadata, hence necessary
        

        im_flipped.save(os.path.join(out_path,'clean_' + f))
        

def Main():
    path = input("Enter the path to the images: \n")
    meta_strip(path)
    print('Files imported and saved to folder stripped-data and EXIF saved to EXIF.csv')
    t = input("\nPress any key to close the window!")    

if __name__ == "__main__":
    Main()