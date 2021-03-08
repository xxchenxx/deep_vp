import itertools
import argparse
import json
import os
import pickle

import numpy as np

def parse_command_line():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    parser.add_argument('-s', '--start', type=int, default=4)
    parser.add_argument('-e', '--end', type=int, default=6)
    parser.add_argument('-sp', '--start_bcp', type=int, default=1)
    parser.add_argument('-ep', '--end_bcp', type=int, default=11)
    parser.add_argument('bcs_path')
    parser.add_argument('bcp_path')
    args = parser.parse_args()
    return args


def get_projector(vp1, vp2, pp):
    focal = np.sqrt(- np.dot(vp1 - pp, vp2 - pp))

    vp1_w = np.concatenate((vp1, [focal]))
    vp2_w = np.concatenate((vp2, [focal]))
    pp_w = np.concatenate((pp, [0]))

    vp3_w = np.cross(vp1_w-pp_w, vp2_w-pp_w)
    vp3 = np.concatenate((vp3_w[0:2]/vp3_w[2]*focal + pp_w[0:2], [1]))
    vp3_direction = np.concatenate((vp3[0:2], [focal]))-pp_w
    road_plane = np.concatenate((vp3_direction/np.linalg.norm(vp3_direction), [10]))

    def _projector(p):
        if len(p) > 2:
            p = p/p[2]
        p_w = np.concatenate((p[0:2], [focal]))
        dirVec = p_w - pp_w
        t = -np.dot(road_plane, np.concatenate((pp_w, [1])))/np.dot(road_plane[0:3], dirVec)
        return pp_w + t*dirVec

    return _projector


def get_system_projector(data):
    vp1 = np.array(data["camera_calibration"]["vp1"])
    vp2 = np.array(data["camera_calibration"]["vp2"])
    pp = np.array(data["camera_calibration"]["pp"])

    return get_projector(vp1, vp2, pp)


def eval_pure_calibration(distances, projector):
    rel_errors = []
    abs_errors = []

    for ind1, ind2 in itertools.combinations(range(len(distances)), 2):
        image_dist1 = np.linalg.norm(projector(distances[ind1]["p1"]) - projector(distances[ind1]["p2"]))
        image_dist2 = np.linalg.norm(projector(distances[ind2]["p1"]) - projector(distances[ind2]["p2"]))
        image_ratio = image_dist1 / image_dist2
        real_ratio = distances[ind1]["distance"] / distances[ind2]["distance"]
        rel_errors.append(abs(image_ratio - real_ratio) / real_ratio * 100)
        abs_errors.append(abs(image_ratio - real_ratio))
    return rel_errors, abs_errors


def valid_system(system):
    if not '.json' in system:
        return False
    if 'optimal' in system or 'Manual' in system:
        return False
    if 'dubska' in system or 'Sochor' in system or 'VPout' in system or 'Bartl' in system:
        return True
    else:
        return False


def eval_session_bcs(path, session):
    gt_data_path = os.path.join(path, 'dataset', session, 'gt_data.pkl')
    with open(gt_data_path, 'rb') as f:
        gt_data = pickle.load(f, encoding='latin-1', fix_imports=True)
    distance_measurement = gt_data["distanceMeasurement"]

    results_path = os.path.join(path, 'results', session)
    systems = [system for system in os.listdir(results_path) if valid_system(system)]

    out = {}

    for system in systems:
        system_path = os.path.join(results_path, system)
        with open(system_path, 'r') as f:
            system_data = json.load(f)

        projector = get_system_projector(system_data)
        rel_errors, abs_errors = eval_pure_calibration(distance_measurement, projector)
        out[system] = {'rel_errors': rel_errors, 'abs_errors': abs_errors}

    return out

def eval_session_bcp(path, session):
    gt_data_path = os.path.join(path, 'ground_truth', session, 'gt_pairs.json')
    with open(gt_data_path, 'rb') as f:
        gt_data = json.load(f)
    distance_measurement = gt_data

    results_path = os.path.join(path, 'results', session)
    systems = [system for system in os.listdir(results_path) if valid_system(system)]

    out = {}

    for system in systems:
        system_path = os.path.join(results_path, system)
        with open(system_path, 'r') as f:
            system_data = json.load(f)

        projector = get_system_projector(system_data)
        rel_errors, abs_errors = eval_pure_calibration(distance_measurement, projector)
        out[system] = {'rel_errors': rel_errors, 'abs_errors': abs_errors}

    return out

def eval_calib():
    args = parse_command_line()

    print("**************************")
    print("Eval BrnoCompSpeed")
    print("**************************")

    sessions = []
    for i in range(args.start, args.end + 1):
        sessions.append('session{}_center'.format(i))
        sessions.append('session{}_left'.format(i))
        sessions.append('session{}_right'.format(i))

    results = {}

    for session in sessions:
        results[session] = eval_session_bcs(args.bcs_path, session)

    systems = results[sessions[0]].keys()

    for system in systems:
        # print("For system ", system)

        rel_errors = []
        abs_errors = []

        for session in sessions:
            rel_errors.extend(results[session][system]['rel_errors'])
            abs_errors.extend(results[session][system]['abs_errors'])

            # rel_errors.append(np.mean(results[session][system]['rel_errors']))
            # abs_errors.append(np.mean(results[session][system]['abs_errors']))

            # print("{}: mean rel err: {}, median rel err {}, mean abs err {}, median abs err {}".format(session,
            #     np.mean(results[session][system]['rel_errors']), np.median(results[session][system]['rel_errors']),
            #     np.mean(results[session][system]['abs_errors']), np.median(results[session][system]['abs_errors'])))

        print("For {} mean rel err: {}, median rel err {}, mean abs err {}, median abs err {}".format(system,
            np.mean(rel_errors), np.median(rel_errors),
            np.mean(abs_errors), np.median(abs_errors)))

    print("**************************")
    print("Eval BrnoCarPark")
    print("**************************")


    sessions = ['S{:02d}'.format(i) for i in range(args.start_bcp, args.end_bcp + 1)]

    for session in sessions:
        results[session] = eval_session_bcp(args.bcp_path, session)

        systems = results[sessions[0]].keys()

    for system in systems:
        # print("For system ", system)

        rel_errors = []
        abs_errors = []

        for session in sessions:
            rel_errors.extend(results[session][system]['rel_errors'])
            abs_errors.extend(results[session][system]['abs_errors'])

            # rel_errors.append(np.mean(results[session][system]['rel_errors']))
            # abs_errors.append(np.mean(results[session][system]['abs_errors']))

            # print(system, session, np.isnan(rel_errors).any())
            # print("{}: mean rel err: {}, median rel err {}, mean abs err {}, median abs err {}".format(session,
            #     np.mean(results[session][system]['rel_errors']), np.median(results[session][system]['rel_errors']),
            #     np.mean(results[session][system]['abs_errors']), np.median(results[session][system]['abs_errors'])))

        print("For {} mean rel err: {}, median rel err {}, mean abs err {}, median abs err {}".format(system,
            np.nanmean(rel_errors), np.nanmedian(rel_errors),
            np.nanmean(abs_errors), np.nanmedian(abs_errors)))



if __name__ == '__main__':
    eval_calib()