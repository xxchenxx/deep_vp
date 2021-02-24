import os

import numpy as np

from models.hourglass import parse_command_line, load_model
from utils.diamond_space import process_heatmaps
from utils.reg_dataset import RegBoxCarsDataset

def eval():
    args = parse_command_line()
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu

    scales = [0.03, 0.1, 0.3, 1.0]

    model, snapshot_dir_name, _ = load_model(args, scales)
    print("Heatmap model loaded")

    test_dataset = RegBoxCarsDataset(args.path, 'test', batch_size=32, img_size=args.input_size, num_stacks=1,
                                     use_diamond=False)

    gt_vp_list = []
    pred_vp_list = []
    pred_dists_vars = []

    for X, gt_vp in test_dataset:
        pred = model.predict(X)
        pred_vps, pred_dists = process_heatmaps(pred[-1], scales)

        gt_vp_list.append(gt_vp[0])
        pred_vp_list.append(pred_vps)
        pred_dists_vars.append(pred_dists)

    gt_vps = np.concatenate(gt_vp_list, axis=0)
    pred_vps = np.concatenate(pred_vp_list, axis=0)
    pred_vars = np.concatenate(pred_dists_vars, axis=0)

    diff = pred_vps - gt_vps[:, np.newaxis, :]
    diff[np.isinf(diff)] = np.nan
    vp1_d = np.linalg.norm(diff[:, :, :2], axis=-1)
    vp2_d = np.linalg.norm(diff[:, :, 2:], axis=-1)

    vp1_gt_norm = np.linalg.norm(gt_vps[:, :2], axis=-1)
    vp2_gt_norm = np.linalg.norm(gt_vps[:, 2:], axis=-1)

    for j, scale in enumerate(scales):
        print('*' * 80)
        print("For scale: {}".format(scale))
        print("Median vp1 abs distance: {}".format(np.nanmedian(vp1_d[:, j])))
        print("Median vp2 abs distance: {}".format(np.nanmedian(vp2_d[:, j])))
        print("Median vp1 rel distance: {}".format(np.nanmedian(vp1_d[:, j] / vp1_gt_norm)))
        print("Median vp2 rel distance: {}".format(np.nanmedian(vp2_d[:, j] / vp2_gt_norm)))
        
    vp1_var = pred_vars[:, :, 0]
    vp2_var = pred_vars[:, :, 1]
    vp1_var_idx = np.argmin(vp1_var, axis=-1)
    vp2_var_idx = np.argmin(vp2_var, axis=-1)

    print('*' * 80)
    print('For optimal var scale')
    print("Median vp1 abs distance: {}".format(np.nanmedian(vp1_d[:, vp1_var_idx])))
    print("Median vp2 abs distance: {}".format(np.nanmedian(vp2_d[:, vp2_var_idx])))
    print("Median vp1 rel distance: {}".format(np.nanmedian(vp1_d[:, vp1_var_idx] / vp1_gt_norm)))
    print("Median vp2 rel distance: {}".format(np.nanmedian(vp2_d[:, vp2_var_idx] / vp2_gt_norm)))
    
    vp1_d_idx = np.argmin(vp1_d, axis=-1)
    vp2_d_idx = np.argmin(vp2_d, axis=-1)
    
    print('*' * 80)
    print('For optimal gt scale')

    print("Median vp1 abs distance: {}".format(np.nanmedian(vp1_d[:, vp1_d_idx])))
    print("Median vp2 abs distance: {}".format(np.nanmedian(vp2_d[:, vp2_d_idx])))
    print("Median vp1 rel distance: {}".format(np.nanmedian(vp1_d[:, vp1_d_idx] / vp1_gt_norm)))
    print("Median vp2 rel distance: {}".format(np.nanmedian(vp2_d[:, vp2_d_idx] / vp2_gt_norm)))


if __name__ == '__main__':
    eval()