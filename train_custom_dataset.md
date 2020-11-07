1. create /lib/dataset/[dataset].py
 Copy pascal_voc.py file

Line 35: add name's categories of custom dataset
Line 67: image_path = os.path.join(self._data_path,'[dataset]', 'Images',
                              index + self._image_ext)
Line 79: image_set_file = os.path.join(self._data_path,'[dataset]', 'ImageSets',
                                  self._image_set + '.txt')
Line 141:  filename = os.path.join(self._data_path,'[dataset]', 'Annotations', index + '.xml')

Line 164-167:if your dataset start with 0
	# Make pixel indexes 0-based
      x1 = float(bbox.find('xmin').text)
      y1 = float(bbox.find('ymin').text)
      x2 = float(bbox.find('xmax').text)
      y2 = float(bbox.find('ymax').text)

Line 216: annopath = os.path.join(
      self._devkit_path,'[dataset]/'
      'Annotations',
      '{:s}.xml')
Line 220: self._devkit_path,[dataset]/'


2. /lib/dataset/factory.py
set up custom dataset:
add 

from datasets.coin_banknote import coin_banknote


for split in ['train','test']:
  name = '[dataset]_{}'.format(split)
  __sets[name] = (lambda split=split: (dataset)(split))

3. /lib/dataset/imdb.py
Line 116-117: if your dataset start with 0
boxes[:, 0] = widths[i] - oldx2
      boxes[:, 2] = widths[i] - oldx1


4. experiments/scripts/train_faster_rcnn.sh
Line 42:
dataset)
    TRAIN_IMDB="[dataset]_train"
    TEST_IMDB="[dataset]_test"
    STEPSIZE="[80000]"
    ITERS=110000
    ANCHORS="[8,16,32]"
    RATIOS="[0.5,1,2]"
    ;;

5. experiments/scripts/test_faster_rcnn.sh
coin_banknote)
    TRAIN_IMDB="train"
    TEST_IMDB="[dataset]_test"
    STEPSIZE="[80000]"
    ITERS=110000
    ANCHORS="[8,16,32]"
    RATIOS="[0.5,1,2]"
    ;;