import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch
from tqdm import tqdm
from pathlib import Path
import os
os.environ['CUDA_VISIBLE_DEVICES'] = "1"

openpose_dir = Path('src/PoseEstimation/')
mainpath = os.getcwd()

save_dir = Path(mainpath+'/data/target/')
save_dir.mkdir(exist_ok=True)

img_dir = save_dir.joinpath('images')
img_dir.mkdir(exist_ok=True)

if len(os.listdir(mainpath+'/data/target/images'))<100:
    cap = cv2.VideoCapture(str(save_dir.joinpath('mv.mp4')))
    i = 0
    while (cap.isOpened()):
        flag, frame = cap.read()
        if flag == False and i == 1200:
            break
        cv2.imwrite(str(img_dir.joinpath('img_%d.png' % i)), frame)
        i += 1

import sys
sys.path.append(str(openpose_dir))
sys.path.append('./src/utils')
# openpose
from network.rtpose_vgg import get_model
from evaluate.coco_eval import get_multiplier, get_outputs

# utils
from openpose_utils import remove_noise, get_pose

weight_name = './src/PoseEstimation/network/weight/pose_model.pth'

model = get_model('vgg19')
model.load_state_dict(torch.load(weight_name))
model = torch.nn.DataParallel(model).cuda()
model.float()
model.eval()
pass

save_dir = Path('./data/target/')
save_dir.mkdir(exist_ok=True)

img_dir = save_dir.joinpath('images')
img_dir.mkdir(exist_ok=True)


'''make label images for pix2pix'''
train_dir = save_dir.joinpath('train')
train_dir.mkdir(exist_ok=True)

train_img_dir = train_dir.joinpath('train_img')
train_img_dir.mkdir(exist_ok=True)
train_label_dir = train_dir.joinpath('train_label')
train_label_dir.mkdir(exist_ok=True)

for idx in tqdm(range(150, 1150)):
    img_path = img_dir.joinpath('img_%d.png'%idx)
    img = cv2.imread(str(img_path))
    shape_dst = np.min(img.shape[:2])
    oh = (img.shape[0] - shape_dst) // 2
    ow = (img.shape[1] - shape_dst) // 2

    img = img[oh:oh + shape_dst, ow:ow + shape_dst]
    img = cv2.resize(img, (512, 512))
    multiplier = get_multiplier(img)
    with torch.no_grad():
        paf, heatmap = get_outputs(multiplier, img, model, 'rtpose')
    r_heatmap = np.array([remove_noise(ht)
                          for ht in heatmap.transpose(2, 0, 1)[:-1]]) \
        .transpose(1, 2, 0)
    heatmap[:, :, :-1] = r_heatmap
    param = {'thre1': 0.1, 'thre2': 0.05, 'thre3': 0.5}
    label = get_pose(param, heatmap, paf)

    cv2.imwrite(str(train_img_dir.joinpath('img_%d.png'%idx)), img)
    cv2.imwrite(str(train_label_dir.joinpath('label_%d.png'%idx)), label)

torch.cuda.empty_cache()