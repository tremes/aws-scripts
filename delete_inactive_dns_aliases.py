#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError

def list_loadbalancers(region='us-east-1'):
    """Lists all the active AWS loadbalancerts in 
    the given region. Returns a dictionary when key is the DNS name 
    of the loadbalancer. """
    elbv2_client = boto3.client('elbv2', region_name=region)
    elb_client = boto3.client('elb', region_name=region)
    loadbalancer_map = {}

    try:
        response = elbv2_client.describe_load_balancers()
        for lb in response['LoadBalancers']:
            if lb['State']['Code'] == 'active':
                loadbalancer_map[lb['DNSName']] = {
                    'type': lb['Type'],
                    'arn': lb['LoadBalancerArn'],
                    'dns_name': lb['DNSName']
                }

        response = elb_client.describe_load_balancers()
        for lb in response['LoadBalancerDescriptions']:
            loadbalancer_map[lb['DNSName']] = {
                'type': 'classic',
                'dns_name': lb['DNSName']
            }

    except Exception as e:
        print(f"Error: {e}")
        return {}

    return loadbalancer_map

def get_public_hosted_zones():
    """Get all public hosted zones."""
    route53 = boto3.client('route53')

    try:
        response = route53.list_hosted_zones()
        public_zones = []

        for zone in response['HostedZones']:
            if not zone['Config']['PrivateZone']:
                public_zones.append({
                    'Id': zone['Id'],
                    'Name': zone['Name'],
                    'RecordCount': zone['ResourceRecordSetCount']
                })

        return public_zones
    except ClientError as e:
        print(f"Error listing hosted zones: {e}")
        return []


def get_dns_records(zone_id):
    """Get all DNS records for a specific hosted zone."""
    route53 = boto3.client('route53')

    try:
        paginator = route53.get_paginator('list_resource_record_sets')
        all_records = []

        for page in paginator.paginate(HostedZoneId=zone_id):
            all_records.extend(page['ResourceRecordSets'])

        return all_records
    except ClientError as e:
        print(f"Error getting records for zone {zone_id}: {e}")
        return []

def main():
    lb_map = list_loadbalancers()

    # print("Active Load Balancers:")
    # for name, details in lb_map.items():
    #     print(f"  {name}: {details['type']} - {details['dns_name']}")


    # Get all public hosted zones
    zones = get_public_hosted_zones()

    if not zones:
        print("No public hosted zones found or error occurred.")
        return

    all_a_dns_records = []

    if len(zones) != 1:
        print("There is more than 1 public zone. Script will not do anything!")
        return
    public_zone = zones[0]
    
    print(f"\nProcessing zone: {public_zone['Name']} (ID: {public_zone['Id']})")

    # Get records for this zone
    records = get_dns_records(public_zone['Id'])

    print(f"Total number of DNS records is {len(records)}")

    for record in records:
        if record["Type"] == "A":
            all_a_dns_records.append(record)
                
    records_to_be_removed = []
    for r in all_a_dns_records:
        dns_name = r["AliasTarget"]["DNSName"]
        dns_name = dns_name.removesuffix(".")
        # check if the DNS name is in the list of active loadbalancers
        if lb_map.get(dns_name) is None:
            records_to_be_removed.append(r)
    
    print(f"{len(records_to_be_removed)} DNS records can be removed")
    print()
    
    client = boto3.client('route53')
    
    for r in records_to_be_removed:
        response = client.change_resource_record_sets(
            HostedZoneId=public_zone['Id'],
            ChangeBatch={
                'Changes': [{
                    'Action': 'DELETE',
                    'ResourceRecordSet': r
                }]
            }
        )
        if response['ResponseMetadata']['HTTPStatusCode']==200:
            print(f"Successfully removed DNS record {r['Name']}")
    
if __name__ == "__main__":
    main()