# Chord-DHT

A peer-to-peer file sharing system built on a Chord-style Distributed Hash Table (DHT), implemented in Python. The system uses consistent hashing to distribute files across nodes in a ring topology, and is designed to be resilient to node joins, leaves, and failures.

> Built as part of a Network-Centric Computing course assignment (Spring 2026). Repository shared for portfolio purposes.

## Overview

This project implements a distributed key-value store where each node is responsible for a contiguous range of the hash space. Files are placed and retrieved using consistent hashing, so the system scales without requiring a full redistribution of data when nodes join or leave.

## Features

- **Consistent Hashing** — Nodes and files are hashed into a fixed-size ring (`M`-bit key space), with each node owning the space between itself and its predecessor.
- **Join Protocol** — New nodes locate their position in the ring via lookup, update successor/predecessor pointers, and receive their share of files from the previously responsible node.
- **Graceful Leave** — Departing nodes notify their predecessor and successor, and transfer their files to the new responsible node before exiting the ring.
- **Failure Detection & Recovery** — Nodes periodically ping their successor; after repeated missed pings, the node fails over to a backup successor. Files are replicated to a neighboring node so no data is lost on failure.
- **Socket-Based Communication** — All inter-node communication (lookups, pings, file transfer) happens over TCP sockets — no direct access to another node's internal state.
- **Put / Get API** — Standard key-value operations: `put()` locates the responsible node and stores a file; `get()` locates and retrieves it.

## Architecture

Each node maintains:

| Field | Description |
|---|---|
| `host`, `port` | Node's network address |
| `key` | Hashed identifier of the node |
| `successor` / `predecessor` | Addresses of neighboring nodes in the ring |
| `files` | Files this node is primarily responsible for |
| `backup_files` | Replicated files held for fault tolerance |

Core operations (`join`, `leave`, `put`, `get`) all route through a shared lookup function that walks the ring to find the node responsible for a given key.

## Getting Started

### Requirements
- Python 3
- (Optional) Docker, for a consistent test environment

### Running a Node
```bash
python3 check.py <port>
```

### Running Multiple Nodes Concurrently
```bash
python3 run_multiple_tests.py <port1> <port2> <port3> ...
```

### Running via Docker
```bash
docker compose run --rm netcen-spring-2026
```

## Testing

The test suite covers:
- Node initialization
- Join (single-node, two-node, and general N-node cases)
- Put / Get correctness
- File transfer on join
- Graceful leave with correct file handoff
- Failure detection and file recovery on backup nodes

## Notes

- File placement follows a strict rule: each file exists on exactly one primary node and one backup node — no more, no fewer.
- Ring pointers are maintained and repaired dynamically via periodic pinging rather than a static configuration.

## License

MIT
