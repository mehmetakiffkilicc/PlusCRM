#!/usr/bin/env python3
"""
TCP-to-SOCKS5 bridge for Tailscale userspace networking.
Listens on a local port and forwards connections through
Tailscale's SOCKS5 proxy to the target SQL Server.
No external dependencies required - uses only Python stdlib.
"""
import socket
import struct
import threading
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tcp_bridge")

SOCKS5_HOST = "127.0.0.1"
SOCKS5_PORT = 1055
BUFFER_SIZE = 65536


def socks5_connect(target_host, target_port):
    """Create a TCP connection through the Tailscale SOCKS5 proxy."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((SOCKS5_HOST, SOCKS5_PORT))

    # SOCKS5 greeting: version=5, 1 auth method, method=0 (no auth)
    sock.sendall(b'\x05\x01\x00')
    resp = sock.recv(2)
    if resp != b'\x05\x00':
        sock.close()
        raise Exception(f"SOCKS5 auth negotiation failed: {resp.hex()}")

    # SOCKS5 connect request: ver=5, cmd=1(connect), rsv=0, atyp=1(IPv4)
    ip_bytes = socket.inet_aton(target_host)
    port_bytes = struct.pack('!H', target_port)
    sock.sendall(b'\x05\x01\x00\x01' + ip_bytes + port_bytes)

    # Read response (minimum 10 bytes for IPv4)
    resp = sock.recv(10)
    if len(resp) < 2:
        sock.close()
        raise Exception("SOCKS5 connect: empty response")
    if resp[1] != 0x00:
        error_codes = {
            0x01: "general failure",
            0x02: "connection not allowed",
            0x03: "network unreachable",
            0x04: "host unreachable",
            0x05: "connection refused",
            0x06: "TTL expired",
            0x07: "command not supported",
            0x08: "address type not supported",
        }
        err = error_codes.get(resp[1], f"unknown error {resp[1]}")
        sock.close()
        raise Exception(f"SOCKS5 connect failed: {err}")

    sock.settimeout(None)
    return sock


def forward(src, dst, name=""):
    """Forward data bidirectionally between two sockets."""
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            src.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            dst.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass


def handle_client(client_sock, target_host, target_port):
    """Handle a single incoming client connection."""
    try:
        remote = socks5_connect(target_host, target_port)
        logger.info(f"Bridge connected to {target_host}:{target_port} via SOCKS5")

        t1 = threading.Thread(target=forward, args=(client_sock, remote, "c->r"), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client_sock, "r->c"), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        logger.error(f"Bridge connection error: {e}")
        try:
            client_sock.close()
        except Exception:
            pass


def main():
    listen_port = int(os.environ.get('SQL_PORT', '14330'))
    target_host = os.environ.get('TAILSCALE_TARGET_IP', '100.109.143.127')
    target_port = int(os.environ.get('SQL_REMOTE_PORT', '14330'))

    # Wait briefly for SOCKS5 proxy to be ready
    time.sleep(2)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', listen_port))
    server.listen(5)

    logger.info(f"SOCKS5 TCP bridge listening on 0.0.0.0:{listen_port}")
    logger.info(f"Forwarding to {target_host}:{target_port} via SOCKS5 proxy at {SOCKS5_HOST}:{SOCKS5_PORT}")

    while True:
        try:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, target_host, target_port), daemon=True)
            t.start()
        except Exception as e:
            logger.error(f"Accept error: {e}")


if __name__ == '__main__':
    main()
