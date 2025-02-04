#!/usr/bin/env python
import os
import pdb
import json
import torch
import pprint
import argparse
import importlib
import numpy as np

import matplotlib
matplotlib.use("Agg")

from config import system_configs
from nnet.py_factory import NetworkFactory
from db.datasets import datasets

torch.backends.cudnn.benchmark = False
torch.set_num_threads(256)


def parse_args():
    parser = argparse.ArgumentParser(description="Test CornerNet")
    parser.add_argument("--cfg_file", help="config file", type=str)
    parser.add_argument("--testiter", dest="testiter",
                        help="test at iteration i",
                        default=None, type=int)
    parser.add_argument("--split", dest="split",
                        help="which split to use",
                        default="validation", type=str)
    parser.add_argument("--no_flip", help="do not flip image", action="store_true")
    parser.add_argument("--suffix", dest="suffix", default=None, type=str)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--data_url", type=str)
    parser.add_argument("--num_gpus", type=str)
    parser.add_argument("--train_url", type=str)

    args = parser.parse_args()
    return args

def make_dirs(directories):
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

def test(db, cfg_file, split, testiter, debug=False, no_flip = False, suffix=None): 
    result_dir = csv_dir = system_configs.result_dir
    result_dir = os.path.join(result_dir, str(testiter), split)
    # csv_dir = os.path.join(result_dir, "csv_results")

    if suffix is not None:
        result_dir = os.path.join(result_dir, suffix)

    make_dirs([result_dir, csv_dir])

    test_iter = system_configs.max_iter if testiter is None else testiter
    print("loading parameters at iteration: {}".format(test_iter))

    print("building neural network...")
    nnet = NetworkFactory(db)
    print("loading parameters...")
    nnet.load_params(test_iter)

    test_file = "test.{}".format(db.data)
    testing = importlib.import_module(test_file).testing

    if torch.cuda.is_available():
        nnet.cuda()
    else:
        print("CUDA is not available")
    nnet.eval_mode()
    testing(db, cfg_file , nnet, result_dir, csv_dir, test_iter, debug=debug, no_flip = no_flip)

if __name__ == "__main__":
    args = parse_args()

    if args.suffix is None:
        cfg_file = os.path.join(system_configs.config_dir, args.cfg_file + ".json")
    else:
        cfg_file = os.path.join(system_configs.config_dir, args.cfg_file + "-{}.json".format(args.suffix))
    print("cfg_file: {}".format(cfg_file))

    with open(cfg_file, "r") as f:
        configs = json.load(f)
            
    configs["system"]["snapshot_name"] = args.cfg_file
    system_configs.update_config(configs["system"])
    system_configs.update_config(configs["db"])

    train_split = system_configs.train_split
    val_split   = system_configs.val_split
    test_split  = system_configs.test_split

    split = {
        "training": train_split,
        "validation": val_split,
        "testing": test_split
    }[args.split]

    print("loading all datasets...")
    dataset = system_configs.dataset
    print("split: {}".format(split))
    testing_db = datasets[dataset](configs["db"], split)

    print("system config...")
    pprint.pprint(system_configs.full)

    print("db config...")
    pprint.pprint(testing_db.configs)
    
    test(testing_db, args.cfg_file, args.split, args.testiter, args.debug, args.no_flip, args.suffix)
