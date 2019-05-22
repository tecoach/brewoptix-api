#!/bin/python3
import argparse
from argparse import RawTextHelpFormatter

import os
import sys
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dynamodb_json import json_util
import shlex
from subprocess import Popen, PIPE
import time
import random


ignore_script_upto = 49


def run_cmd(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    process = Popen(args, stdout=PIPE)

    while True:
        output = process.stdout.readline().rstrip().decode('utf-8')
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output)

    exitcode = process.poll()

    return exitcode


def get_current_version(stage):
    config_filename = 'config.' + stage + '.json'
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    config_filepath = os.path.join(parent_dir, config_filename)

    try:
        with open(config_filepath, 'r') as fp:
            config = json.load(fp)
    except FileNotFoundError as ex:
        print(str(ex))
        sys.exit(1)

    region = config['REGION']

    resource = boto3.resource('dynamodb', region_name=region)
    table = resource.Table('brewoptix-deployment')

    current_version = 0
    backoff_waits = [0, ]
    while True:
        try:
            response = table.scan(
                FilterExpression=Attr('stage').eq(stage),
                ConsistentRead=True
            )
            backoff_waits = [0, ]
            break
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                print("ProvisionedThroughputExceededException: waiting")
                backoff_waits.append(2 ** (len(backoff_waits) - 1) * 5)
                time.sleep(backoff_waits[random.randint(0, len(backoff_waits) - 1)])
            else:
                raise ex

    for item in response['Items']:
        if 'script_number' in item and item['script_number'] > current_version:
            current_version = item['script_number']

    while 'LastEvaluatedKey' in response:
        backoff_waits = [0, ]
        while True:
            try:
                response = table.scan(
                    FilterExpression=Attr('obj_type').eq(stage),
                    ConsistentRead=True,
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                backoff_waits = [0, ]
                break
            except ClientError as ex:
                if ex.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                    print("ProvisionedThroughputExceededException: waiting")
                    backoff_waits.append(2 ** (len(backoff_waits) - 1) * 5)
                    time.sleep(backoff_waits[random.randint(0, len(backoff_waits) - 1)])
                else:
                    raise ex

        for item in response['Items']:
            if 'script_number' in item and item['script_number'] > current_version:
                current_version = item['script_number']

    first_run = False
    if current_version == 0:
        first_run = True

    if current_version < ignore_script_upto:
        return ignore_script_upto, first_run

    return current_version, first_run


def get_max_version():
    max_version = 0
    for entry in os.listdir("deployment_scripts"):
        try:
            v = int(entry.split('_')[0])
            if v > max_version:
                max_version = v
        except ValueError:
            pass

    return max_version


def check_config_keys(stage):
    # check if config.{stage}.json has all keys described in config.example.json
    with open('config.example.json', 'rt') as fp:
        example_json = json.load(fp)

    config_file = 'config.{STAGE}.json'.format(STAGE=stage)
    with open(config_file, 'rt') as fp:
        stage_json = json.load(fp)

    for k in example_json:
        if k not in stage_json.keys():
            print("WARNING: Key {K} not found in {FILE}".format(K=k, FILE=config_file))


def run(stage, silent=False, update_to=0):
    check_config_keys(stage)
    failed_scripts = ""
    missing_scripts = ""
    failure = False
    missing = False

    print("Checking for deployment scripts to be run...")
    current_version, first_run = get_current_version(stage)
    max_version = get_max_version()

    if max_version <= current_version:
        print("Current version: {CUR_VERSION} is the latest. Exiting...".format(CUR_VERSION=current_version))
        sys.exit(0)

    if update_to == 0:
        update_to = max_version

    if update_to <= current_version:
        print("Current version: {CUR_VERSION} is greater than or equal to "
              "the version you wish to Update to: {UPDATE_TO}. Exiting...".format(CUR_VERSION=current_version, UPDATE_TO=update_to))
        sys.exit(0)

    if not silent:
        while True:
            if first_run:
                print("This looks like a new environment. Deploy System and ")

            ans = input("Run updates {CUR_VERSION_PLUS_ONE} to {UPDATE_TO}. Do you wish to continue (y or n)? ".format(
                CUR_VERSION_PLUS_ONE=current_version + 1,
                UPDATE_TO=update_to
            ))
            if ans in ['y', 'Y']:
                break
            elif ans in ['n', 'N']:
                sys.exit(0)
            else:
                print("Please answer y or n.")

    # compatibility patch, ignores first many versions of brewoptix deployment scripts
    min_compatible_version = 1
    if ignore_script_upto > min_compatible_version:
        min_compatible_version = ignore_script_upto + 1

    scripts_dict = dict()
    for f in os.listdir("deployment_scripts"):
        if os.path.splitext(f)[-1] == '.sh':
            try:
                script_num = int(f.split("_")[0])
                if script_num < min_compatible_version:
                    continue
            except ValueError:
                continue

            scripts_dict[script_num] = f

    if first_run:
        if not silent:
            print("Running system deployment script")

        cmd = "sh deployment_scripts/common/deploy_system.sh {STAGE}".format(STAGE=stage)
        exitcode = run_cmd(cmd)

        if exitcode:
            failed_scripts += "common/deploy_system.sh {STAGE}\n".format(STAGE=stage)
            failure = True

    for script_num in range(min_compatible_version, max_version+1):
        try:
            entry = scripts_dict[script_num]
        except KeyError:
            missing_scripts += "{SCRIPT_NUM}, ".format(SCRIPT_NUM=script_num)
            missing = True
            continue

        try:
            entry_version = int(entry.split('_')[0])
            if entry_version > current_version:
                if entry_version <= update_to:
                    if not silent:
                        print("Running deployment script: {0}".format(entry))

                    cmd = "sh deployment_scripts/{SCRIPT} {STAGE}".format(SCRIPT=entry, STAGE=stage)
                    exitcode = run_cmd(cmd)

                    if exitcode:
                        failed_scripts += "{SCRIPT} {STAGE}\n".format(SCRIPT=entry, STAGE=stage)
                        failure = True
        except ValueError:
            pass

    print("Summary: ")
    if failure:
        print("The following scripts failed. Please fix service and deploy manually")
        print(failed_scripts)

    if missing:
        print("Scripts for the following script numbers are missing. Please add them to successfully deploy services")
        print(missing_scripts)

    if not failure and not missing:
        print("All updates deployed successfully")


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                     description='''Deploy a new environment or Update existing environment
    Examples:
    python deploy.py -e test --update-to 4
    python deploy.py --stage dev --silent
    python deploy.py --stage prod''')

    # Add the arguments
    parser.add_argument('stage', metavar='STAGE', type=str,
                        help='environment to deploy to')
    parser.add_argument('-v', '--version',  action='store_true', help='get the current version of the environment')
    parser.add_argument('-u', '--update-to', type=int, default=0, help='update to following version')
    parser.add_argument('-s', '--silent', action='store_true', help='update to latest without prompt')

    # Execute the parse_args() method
    args = parser.parse_args()

    stage = args.stage

    if args.version:
        version, _ = get_current_version(stage)
        print("API version: {0}".format(version))
    else:
        run(stage, silent=args.silent, update_to=args.update_to)
