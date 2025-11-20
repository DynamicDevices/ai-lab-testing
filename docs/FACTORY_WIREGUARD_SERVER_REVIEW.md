# Factory WireGuard Server - Source Code Review

## Repository
https://github.com/foundriesio/factory-wireguard-server

## Purpose
A simple tool to manage Factory VPN connections to devices from an internet connected server based on WireGuard.

## Key Finding from README

**CRITICAL:** "NOTE: devices can only access the VPN server. They can't see/access each other."

This explains why client-to-device communication isn't working by default!

## Architecture

The daemon (`factory-wireguard.py daemon`) maintains:
- WireGuard peer configuration
- `/etc/hosts` file with device hostnames/IPs
- Syncs device settings from FoundriesFactory API

## Need to Review

1. How peers are configured (allowed-ips)
2. How the daemon manages peer-to-peer communication
3. Whether there's a way to enable device-to-device communication
4. How client peers are handled
