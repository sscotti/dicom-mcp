#!/usr/bin/env python3
from pynetdicom import AE, debug_logger
import os
import socket

debug_logger()

# Check if we're in Docker
in_docker = os.path.exists('/.dockerenv')
hostname = 'dicom-mwl-mpps' if in_docker else 'localhost'
port = 104 if in_docker else 4104

print(f"Environment: {'Docker' if in_docker else 'Host'}")
print(f"Testing DNS resolution for {hostname}...")

try:
    ip_address = socket.gethostbyname(hostname)
    print(f"{hostname} resolves to: {ip_address}")
except Exception as e:
    print(f"DNS resolution failed: {e}")
    exit(1)

# Test with hostname
print(f"\n=== Testing with hostname: {hostname}:{port} ===")
ae = AE()
ae.add_requested_context('1.2.840.10008.5.1.4.31')
assoc = ae.associate(hostname, port)
print('Hostname connection established:', assoc.is_established)
if assoc.is_established:
    assoc.release()

# Test with IP address
print(f"\n=== Testing with IP address: {ip_address}:{port} ===")
ae = AE()  
ae.add_requested_context('1.2.840.10008.5.1.4.31')
assoc = ae.associate(ip_address, port)
print('IP address connection established:', assoc.is_established)
if assoc.is_established:
    assoc.release()
    print('Successfully connected and released!') 