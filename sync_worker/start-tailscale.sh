#!/bin/sh

# Start tailscaled in the background
tailscaled --state=mem: --tun=userspace-networking --socks5-server=localhost:1055 &
TAILSCALED_PID=$!

# Wait for tailscaled to start
sleep 5

# Function to clean up tailscale on exit
cleanup() {
    echo "Caught termination signal, logging out of Tailscale..."
    python log_tailscale.py "Caught signal, logging out of Tailscale to remove ephemeral node..." "INFO"
    tailscale logout
    kill $TAILSCALED_PID
    exit 0
}

# Trap termination signals
trap cleanup TERM INT QUIT

# Connect to Tailscale
if [ -n "$TAILSCALE_AUTHKEY" ]; then
    TS_VERSION=$(tailscale version | head -n 1)
    python log_tailscale.py "Attempting to connect to Tailscale ($TS_VERSION)... Hostname: ${RAILWAY_SERVICE_NAME:-MarketFlow-worker}" "INFO"
    
    # Simplified flags to improve compatibility
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="${RAILWAY_SERVICE_NAME:-MarketFlow-worker}" --accept-dns=true --accept-routes > /tmp/tailscale.log 2>&1

    
    if [ $? -eq 0 ]; then
        STATUS=$(tailscale status)
        python log_tailscale.py "Tailscale connected. Status: $STATUS" "INFO"
    else
        ERROR_LOG=$(cat /tmp/tailscale.log)
        python log_tailscale.py "Tailscale connection failed: $ERROR_LOG" "ERROR"
    fi
    
    # Start socat bridge for SQL Server
    # SQL_PORT is the LOCAL port we listen on (default 14330)
    # SQL_REMOTE_PORT is the ACTUAL port on the target machine (default 1433)
    L_PORT=${SQL_PORT:-14330}
    R_PORT=${SQL_REMOTE_PORT:-14330}
    
    if [ -n "$TAILSCALE_TARGET_IP" ]; then
        python log_tailscale.py "Testing reachability of $TAILSCALE_TARGET_IP:$R_PORT..." "INFO"
        
        # Test TCP and Ping explicitly using a quick python snippet
        python -c "
import socket, subprocess, sys
ip = '$TAILSCALE_TARGET_IP'
port = $R_PORT
# Test Ping
try:
    ping_out = subprocess.check_output(['tailscale', 'ping', '--c', '2', '--timeout', '5s', ip], stderr=subprocess.STDOUT).decode()
    print('PING SUCCESS:\n' + ping_out)
except subprocess.CalledProcessError as e:
    print('PING FAILED:\n' + e.output.decode())

# Test TCP
try:
    s = socket.socket()
    s.settimeout(3)
    s.connect((ip, port))
    s.close()
    print('TCP 1433 OPEN')
except Exception as e:
    print('TCP 1433 CLOSED/FILTERED: ' + str(e))
" > /tmp/reachability.txt 2>&1

        # Log results
        cat /tmp/reachability.txt | python log_tailscale.py "$(cat)" "INFO"
        
        python log_tailscale.py "Starting Python SOCKS5 bridge: localhost:$L_PORT -> $TAILSCALE_TARGET_IP:$R_PORT" "INFO"
        # Use our Python SOCKS5 bridge instead of socat (socat only supports SOCKS4/4A, not SOCKS5)
        python tcp_bridge.py &
    fi
else
    python log_tailscale.py "TAILSCALE_AUTHKEY not set, skipping Tailscale connection." "WARNING"
fi

# Execute the main application in the background
"$@" &
APP_PID=$!

# Wait for the application to finish or for a signal
wait $APP_PID

