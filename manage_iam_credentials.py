#!/usr/bin/env python3
"""
Examples:
    # Create a key, keeping existing keys:
    python manage_iam_credentials.py --create-access-key

    # Create a replacement and permanently delete old keys:
    python manage_iam_credentials.py --create-access-key --delete-old-access-keys

    # Reset and print the console password:
    python manage_iam_credentials.py --rotate-console-password
"""

import argparse

import boto3


def main():
    parser = argparse.ArgumentParser(description='Manage IAM credentials')
    parser.add_argument('--user', help='Defaults to the current IAM user')
    parser.add_argument('--profile', help='AWS profile')
    parser.add_argument('--region', default='us-east-2', help='AWS region (default: us-east-2)')
    parser.add_argument('--create-access-key', action='store_true')
    parser.add_argument('--delete-old-access-keys', action='store_true',
                        help='Delete previous keys after creating a replacement')
    parser.add_argument('--rotate-console-password', action='store_true')
    parser.add_argument('--password-length', type=int, default=32)
    args = parser.parse_args()

    if not (args.create_access_key or args.rotate_console_password):
        parser.error('Select --create-access-key and/or --rotate-console-password')
    if args.delete_old_access_keys and not args.create_access_key:
        parser.error('--delete-old-access-keys requires --create-access-key')

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    iam = session.client('iam')
    user = args.user or iam.get_user()['User']['UserName']

    old_keys = []
    if args.delete_old_access_keys:
        old_keys = iam.list_access_keys(UserName=user)['AccessKeyMetadata']

    if args.create_access_key:
        key = iam.create_access_key(UserName=user)['AccessKey']
        print(f"Access key ID: {key['AccessKeyId']}", flush=True)
        print(f"Secret access key: {key['SecretAccessKey']}", flush=True)

    if args.rotate_console_password:
        password = session.client('secretsmanager').get_random_password(
            PasswordLength=args.password_length,
            RequireEachIncludedType=True,
        )['RandomPassword']
        iam.update_login_profile(UserName=user, Password=password)
        print(f"Console password: {password}", flush=True)

    for old_key in old_keys:
        iam.delete_access_key(UserName=user, AccessKeyId=old_key['AccessKeyId'])
        print(f"Deleted access key: {old_key['AccessKeyId']}", flush=True)


if __name__ == '__main__':
    main()
