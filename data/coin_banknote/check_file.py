import glob, os
import xml.etree.ElementTree as ET

# create file train.txt and text.txt
# path_data is folder contain images
# percentage test is a percentage of images to be used for the test set


# Directory where the data will reside, relative to 'darknet.exe'
path_data = 'Annotations/'

# Populate train.txt and test.txt

for pathAndFilename in glob.iglob(path_data+"/*.xml"):  
    #print(pathAndFilename)
    tree = ET.parse(pathAndFilename)
    root = tree.getroot()
    for elem in root:
        for subelem in elem:
           
            if subelem.tag =="bndbox":
                for i in subelem:
                    if i.tag =="ymin":
                          if i.text == "0":
                              i.text = "1"
                              tree.write(pathAndFilename)
                              print("done")