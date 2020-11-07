"""" Loading MIO-TCD database. """
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
from datasets.imdb import imdb
import datasets.ds_utils as ds_utils
import xml.etree.ElementTree as ET
import numpy as np
import scipy.sparse
import scipy.io as sio
import utils.cython_bbox
import pickle
import subprocess
import uuid
from .voc_eval import voc_eval
from model.config import cfg

import csv
import sys

# ANNO_FILE = 'gt_train.csv'
#ANNO_FILE = 'partial_gt_train.csv'

class coin_banknote(imdb):
  def __init__(self, image_set, devkit_path=None):
    imdb.__init__(self, image_set)
#     self._year = year
    self._image_set = image_set
    self._devkit_path = self._get_default_path() if devkit_path is None \
      else devkit_path
    self._data_path = os.path.join(self._devkit_path, 'coin_banknote')
    self._classes = ('__background__',  # always index 0
                     '1_Yen','5_Yen','10_Yen','50_Yen','100Yen','500_Yen','1,000 Yen','5,000 Yen','10,000 Yen')
    self._class_to_ind = dict(list(zip(self.classes, list(range(self.num_classes)))))
    self._image_ext = '.jpg'
    self._image_index = self._load_image_set_index()
    # Default to roidb handler
    self._roidb_handler = self.selective_search_roidb
    self._salt = str(uuid.uuid4())
    self._comp_id = 'comp4'

    # PASCAL specific config options
    # change to MIO-TCD specific config
    # no 'use_diff' is needed
    self.config = {'cleanup': True,
                   'use_salt': True,
                   'matlab_eval': False,
                   'rpn_file': None,
                   'min_size': 2}

    assert os.path.exists(self._devkit_path), \
      'MIO-TCD parent folder path does not exist: {}'.format(self._devkit_path)
    assert os.path.exists(self._data_path), \
      'Path does not exist: {}'.format(self._data_path)

  def image_path_at(self, i):
    """
    Return the absolute path to image i in the image sequence.
    """
    return self.image_path_from_index(self._image_index[i])

  def image_path_from_index(self, index):
    """
    Construct an image path from the image's "index" identifier.
    """
    # TODO: might need to adjust for testing
    image_path = os.path.join(self._data_path,'Images',
                              index + self._image_ext)
    assert os.path.exists(image_path), \
      'Path does not exist: {}'.format(image_path)
    return image_path

  def _load_image_set_index(self):
        """
        Load the indexes listed in this dataset's image set file.
        """
        # Example path to image set file:
        # self._devkit_path + /VOCdevkit2007/VOC2007/ImageSets/Main/val.txt
        image_set_file = os.path.join(self._data_path, 'ImageSets', 
                                      self._image_set + '.txt')
        assert os.path.exists(image_set_file), \
                'Path does not exist: {}'.format(image_set_file)
        with open(image_set_file) as f:
            image_index = [x.strip() for x in f.readlines()]
        return image_index

  def _get_default_path(self):
    """
    Return the default path where MIO-TCD-Localization is expected to be installed.
    """
    return cfg.DATA_DIR

  def gt_roidb(self):
        """
        Return the database of ground-truth regions of interest.
        This function loads/saves from/to a cache file to speed up future calls.
        """
        cache_file = os.path.join(self.cache_path, self.name + '_gt_roidb.pkl')
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as fid:
                roidb = cPickle.load(fid)
            print ('{} gt roidb loaded from {}'.format(self.name, cache_file))
            return roidb

        gt_roidb = [self._load_pascal_annotation(index)
                    for index in self.image_index]
        with open(cache_file, 'wb') as fid:
            cPickle.dump(gt_roidb, fid, cPickle.HIGHEST_PROTOCOL)
        print ('wrote gt roidb to {}'.format(cache_file))

        return gt_roidb

  def selective_search_roidb(self):
    """
    Return the database of selective search regions of interest.
    Ground-truth ROIs are also included.
    This function loads/saves from/to a cache file to speed up future calls.
    """
    cache_file = os.path.join(self.cache_path,
                              self.name + '_selective_search_roidb.pkl')

    if os.path.exists(cache_file):
      with open(cache_file, 'rb') as fid:
        roidb = pickle.load(fid)
      print('{} ss roidb loaded from {}'.format(self.name, cache_file))
      return roidb

    # TODO: may need to change operation for test
    # if int(self._year) == 2007 or self._image_set != 'test':
    gt_roidb = self.gt_roidb()
    # TODO: change _load_selective_search_roidb
    ss_roidb = self._load_selective_search_roidb(gt_roidb)
    # TODO: change merge_roidbs
    roidb = imdb.merge_roidbs(gt_roidb, ss_roidb)
    # else:
    #   roidb = self._load_selective_search_roidb(None)
    with open(cache_file, 'wb') as fid:
      pickle.dump(roidb, fid, pickle.HIGHEST_PROTOCOL)
    print('wrote ss roidb to {}'.format(cache_file))

    return roidb

  def rpn_roidb(self):
    # TODO: may need update for test
    # if int(self._year) == 2007 or self._image_set != 'test':
    gt_roidb = self.gt_roidb()
    rpn_roidb = self._load_rpn_roidb(gt_roidb)
    roidb = imdb.merge_roidbs(gt_roidb, rpn_roidb)
    # else:
    #   roidb = self._load_rpn_roidb(None)

    return roidb

  def _load_rpn_roidb(self, gt_roidb):
    filename = self.config['rpn_file']
    print('loading {}'.format(filename))
    assert os.path.exists(filename), \
      'rpn data not found at: {}'.format(filename)
    with open(filename, 'rb') as f:
      box_list = pickle.load(f)
    # TODO: change create_roidb_from_box_list
    return self.create_roidb_from_box_list(box_list, gt_roidb)

  # TODO: change this function, but need to find the mat file
  def _load_selective_search_roidb(self, gt_roidb):
    filename = os.path.abspath(os.path.join(cfg.DATA_DIR,
                                            'selective_search_data',
                                            self.name + '.mat'))
    assert os.path.exists(filename), \
      'Selective search data not found at: {}'.format(filename)
    raw_data = sio.loadmat(filename)['boxes'].ravel()

    box_list = []
    for i in range(raw_data.shape[0]):
      boxes = raw_data[i][:, (1, 0, 3, 2)] - 1
      keep = ds_utils.unique_boxes(boxes)
      boxes = boxes[keep, :]
      keep = ds_utils.filter_small_boxes(boxes, self.config['min_size'])
      boxes = boxes[keep, :]
      box_list.append(boxes)

    return self.create_roidb_from_box_list(box_list, gt_roidb)

  def _load_pascal_annotation(self, index):
    """
    Load image and bounding boxes info from XML file in the PASCAL VOC
    format.
    """
    filename = os.path.join(self._data_path, 'Annotations', index + '.xml')
    tree = ET.parse(filename)
    objs = tree.findall('object')
    if not self.config['use_diff']:
      # Exclude the samples labeled as difficult
      non_diff_objs = [
        obj for obj in objs if int(obj.find('difficult').text) == 0]
      # if len(non_diff_objs) != len(objs):
      #     print 'Removed {} difficult objects'.format(
      #         len(objs) - len(non_diff_objs))
      objs = non_diff_objs
    num_objs = len(objs)

    boxes = np.zeros((num_objs, 4), dtype=np.uint16)
    gt_classes = np.zeros((num_objs), dtype=np.int32)
    overlaps = np.zeros((num_objs, self.num_classes), dtype=np.float32)
    # "Seg" area for pascal is just the box area
    seg_areas = np.zeros((num_objs), dtype=np.float32)
    
    # Load object bounding boxes into a data frame.
    for ix, obj in enumerate(objs):
      bbox = obj.find('bndbox')
      # Make pixel indexes 0-based
      x1 = float(bbox.find('xmin').text) - 1
      y1 = float(bbox.find('ymin').text) - 1
      x2 = float(bbox.find('xmax').text) - 1
      y2 = float(bbox.find('ymax').text) - 1
      cls = self._class_to_ind[obj.find('name').text.lower().strip()]
      boxes[ix, :] = [x1, y1, x2, y2]
      gt_classes[ix] = cls
      overlaps[ix, cls] = 1.0
      seg_areas[ix] = (x2 - x1 + 1) * (y2 - y1 + 1)

    overlaps = scipy.sparse.csr_matrix(overlaps)

    return {'boxes': boxes,
            'gt_classes': gt_classes,
            'gt_overlaps': overlaps,
            'flipped': False,
            'seg_areas': seg_areas}

  # # TODO: verify the use of salt
  # def _get_comp_id(self):
  #   comp_id = (self._comp_id + '_' + self._salt if self.config['use_salt']
  #              else self._comp_id)
  #   return comp_id

  # # TODO: verify what is this for and change
  # def _get_voc_results_file_template(self):
  #   # VOCdevkit/results/VOC2007/Main/<comp_id>_det_test_aeroplane.txt
  #   filename = self._get_comp_id() + '_det_' + self._image_set + '_{:s}.txt'
  #   path = os.path.join(
  #     self._devkit_path,
  #     'results',
  #     'VOC' + self._year,
  #     'Main',
  #     filename)
  #   return path

  # # TODO: verify what is this for
  # def _write_voc_results_file(self, all_boxes):
  #   for cls_ind, cls in enumerate(self.classes):
  #     if cls == '__background__':
  #       continue
  #     print('Writing {} VOC results file'.format(cls))
  #     filename = self._get_voc_results_file_template().format(cls)
  #     with open(filename, 'wt') as f:
  #       for im_ind, index in enumerate(self.image_index):
  #         dets = all_boxes[cls_ind][im_ind]
  #         if dets == []:
  #           continue
  #         # the VOCdevkit expects 1-based indices
  #         for k in range(dets.shape[0]):
  #           f.write('{:s} {:.3f} {:.1f} {:.1f} {:.1f} {:.1f}\n'.
  #                   format(index, dets[k, -1],
  #                          dets[k, 0] + 1, dets[k, 1] + 1,
  #                          dets[k, 2] + 1, dets[k, 3] + 1))

  
  # TODO: other functions ...

  def competition_mode(self, on):
    if on:
      self.config['use_salt'] = False
      self.config['cleanup'] = False
      
    else:
      self.config['use_salt'] = True
      self.config['cleanup'] = True