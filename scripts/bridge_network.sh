#!/usr/bin/env bash
set -euo pipefail

# Change INSTANCES for the common case. WAN is usually the same for every
# Linux user and CVD instance on the same host.
WAN="${WAN:-wlp10s0}"
INSTANCES=(1)

# Optional one-off override:
#   CVD_INSTANCES="1 4" ./scripts/bridge_network.sh setup
if [[ -n "${CVD_INSTANCES:-}" ]]; then
  read -r -a INSTANCES <<< "$CVD_INSTANCES"
fi

# Cuttlefish guests use the same internal mobile network:
# guest 10.0.2.15/24 -> gateway 10.0.2.2.
# Put each instance into its own netns so different Linux users can run
# different CVD instance numbers without colliding on 10.0.2.0/24.
GUEST_CIDR="10.0.2.0/24"
GUEST_GW="10.0.2.2/24"

usage() {
  cat <<EOF
Usage:
  $0 [setup|teardown|status] [instance ...]
  $0 [setup|teardown|status] [wan] [instance ...]

Examples:
  # Use the defaults at the top of this file.
  $0

  # Setup instance 4 through the default WAN.
  $0 setup 4

  # Setup instances 1 and 4 through wlp10s0 explicitly.
  $0 setup wlp10s0 1 4

  # Remove network setup for instance 4.
  $0 teardown 4

Notes:
  - Start the CVD instance before running setup so cvd-mtap-XX exists.
  - Instance 4 maps to tap cvd-mtap-04 and namespace cvd-net-04.
  - Each instance gets a unique host-side transit network 172.31.<N>.0/30.
EOF
}

ACTION="${1:-setup}"
if [[ "$ACTION" == "-h" || "$ACTION" == "--help" ]]; then
  usage
  exit 0
fi

case "$ACTION" in
  setup|teardown|status)
    shift || true
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ $# -gt 0 ]]; then
  if [[ "$1" =~ ^[0-9]+$ ]]; then
    INSTANCES=("$@")
  else
    WAN="$1"
    shift
    if [[ $# -gt 0 ]]; then
      INSTANCES=("$@")
    fi
  fi
fi

if [[ "${#INSTANCES[@]}" -eq 0 ]]; then
  echo "No CVD instances configured." >&2
  exit 2
fi

SUDO=()
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  SUDO=(sudo)
fi

run() {
  echo "+ $*"
  "${SUDO[@]}" "$@"
}

rule_exists() {
  local table="$1"
  shift
  "${SUDO[@]}" iptables -t "$table" -C "$@" >/dev/null 2>&1
}

ensure_rule() {
  local table="$1"
  shift
  if ! rule_exists "$table" "$@"; then
    run iptables -t "$table" -A "$@"
  fi
}

delete_rule() {
  local table="$1"
  shift
  while rule_exists "$table" "$@"; do
    run iptables -t "$table" -D "$@"
  done
}

instance_suffix() {
  printf "%02d" "$((10#$1))"
}

normalize_instance() {
  local instance="$1"

  if [[ ! "$instance" =~ ^[0-9]+$ ]]; then
    echo "Instance must be a number: $instance" >&2
    exit 2
  fi

  instance="$((10#$instance))"
  if [[ "$instance" -lt 1 || "$instance" -gt 254 ]]; then
    echo "Instance must be between 1 and 254: $instance" >&2
    exit 2
  fi

  echo "$instance"
}

setup_instance() {
  local instance
  local suffix ns br tap veth peer transit_root transit_peer transit_cidr
  local root_veth_exists peer_exists

  instance="$(normalize_instance "$1")"
  suffix="$(instance_suffix "$instance")"
  ns="cvd-net-$suffix"
  br="cvd-mbr-$suffix"
  tap="cvd-mtap-$suffix"
  veth="cvd-veth-$suffix"
  peer="cvd-vpeer-$suffix"
  transit_root="172.31.$instance.1/30"
  transit_peer="172.31.$instance.2/30"
  transit_cidr="172.31.$instance.0/30"

  if ! "${SUDO[@]}" ip netns list | grep -q "^$ns"; then
    run ip netns add "$ns"
  fi
  run ip netns exec "$ns" ip link set lo up

  root_veth_exists=0
  peer_exists=0
  "${SUDO[@]}" ip link show "$veth" >/dev/null 2>&1 && root_veth_exists=1
  "${SUDO[@]}" ip netns exec "$ns" ip link show "$peer" >/dev/null 2>&1 && peer_exists=1

  if [[ "$root_veth_exists" -ne "$peer_exists" ]]; then
    if [[ "$root_veth_exists" -eq 1 ]]; then
      run ip link del "$veth"
    else
      run ip netns exec "$ns" ip link del "$peer"
    fi
    root_veth_exists=0
    peer_exists=0
  fi

  if [[ "$root_veth_exists" -eq 0 && "$peer_exists" -eq 0 ]]; then
    run ip link add "$veth" type veth peer name "$peer"
    run ip link set "$peer" netns "$ns"
  fi

  run ip addr replace "$transit_root" dev "$veth"
  run ip link set "$veth" up
  run ip netns exec "$ns" ip addr replace "$transit_peer" dev "$peer"
  run ip netns exec "$ns" ip link set "$peer" up
  run ip netns exec "$ns" ip route replace default via "172.31.$instance.1"

  if ! "${SUDO[@]}" ip netns exec "$ns" ip link show "$br" >/dev/null 2>&1; then
    run ip netns exec "$ns" ip link add name "$br" type bridge
  fi
  run ip netns exec "$ns" ip addr replace "$GUEST_GW" dev "$br"
  run ip netns exec "$ns" ip link set "$br" up

  if "${SUDO[@]}" ip link show "$tap" >/dev/null 2>&1; then
    run ip link set "$tap" netns "$ns"
  elif ! "${SUDO[@]}" ip netns exec "$ns" ip link show "$tap" >/dev/null 2>&1; then
    echo "Missing $tap. Start CVD instance $instance before setup." >&2
    exit 1
  fi

  run ip netns exec "$ns" ip link set "$tap" up
  run ip netns exec "$ns" ip link set "$tap" master "$br"

  run sysctl -w net.ipv4.ip_forward=1
  run ip netns exec "$ns" sysctl -w net.ipv4.ip_forward=1

  ensure_rule nat POSTROUTING -s "$transit_cidr" -o "$WAN" -j MASQUERADE
  ensure_rule filter FORWARD -s "$transit_cidr" -o "$WAN" -j ACCEPT
  ensure_rule filter FORWARD -d "$transit_cidr" -i "$WAN" -m state --state RELATED,ESTABLISHED -j ACCEPT

  if ! "${SUDO[@]}" ip netns exec "$ns" iptables -t nat -C POSTROUTING -s "$GUEST_CIDR" -o "$peer" -j MASQUERADE >/dev/null 2>&1; then
    run ip netns exec "$ns" iptables -t nat -A POSTROUTING -s "$GUEST_CIDR" -o "$peer" -j MASQUERADE
  fi
  if ! "${SUDO[@]}" ip netns exec "$ns" iptables -C FORWARD -i "$br" -o "$peer" -j ACCEPT >/dev/null 2>&1; then
    run ip netns exec "$ns" iptables -A FORWARD -i "$br" -o "$peer" -j ACCEPT
  fi
  if ! "${SUDO[@]}" ip netns exec "$ns" iptables -C FORWARD -i "$peer" -o "$br" -m state --state RELATED,ESTABLISHED -j ACCEPT >/dev/null 2>&1; then
    run ip netns exec "$ns" iptables -A FORWARD -i "$peer" -o "$br" -m state --state RELATED,ESTABLISHED -j ACCEPT
  fi

  echo "CVD instance $instance is bridged in $ns. Test with: adb shell ping -c 2 8.8.8.8"
}

teardown_instance() {
  local instance
  local suffix ns veth peer transit_cidr

  instance="$(normalize_instance "$1")"
  suffix="$(instance_suffix "$instance")"
  ns="cvd-net-$suffix"
  veth="cvd-veth-$suffix"
  peer="cvd-vpeer-$suffix"
  transit_cidr="172.31.$instance.0/30"

  delete_rule nat POSTROUTING -s "$transit_cidr" -o "$WAN" -j MASQUERADE
  delete_rule filter FORWARD -s "$transit_cidr" -o "$WAN" -j ACCEPT
  delete_rule filter FORWARD -d "$transit_cidr" -i "$WAN" -m state --state RELATED,ESTABLISHED -j ACCEPT

  if "${SUDO[@]}" ip link show "$veth" >/dev/null 2>&1; then
    run ip link del "$veth"
  elif "${SUDO[@]}" ip netns exec "$ns" ip link show "$peer" >/dev/null 2>&1; then
    run ip netns exec "$ns" ip link del "$peer"
  fi

  if "${SUDO[@]}" ip netns list | grep -q "^$ns"; then
    run ip netns del "$ns"
  fi
}

status_instance() {
  local instance
  local suffix ns

  instance="$(normalize_instance "$1")"
  suffix="$(instance_suffix "$instance")"
  ns="cvd-net-$suffix"

  echo "== CVD instance $instance ($ns) =="
  "${SUDO[@]}" ip netns exec "$ns" ip -br addr 2>/dev/null || true
  "${SUDO[@]}" ip netns exec "$ns" bridge link show 2>/dev/null || true
  "${SUDO[@]}" ip -br addr show "cvd-veth-$suffix" 2>/dev/null || true
}

for instance in "${INSTANCES[@]}"; do
  case "$ACTION" in
    setup) setup_instance "$instance" ;;
    teardown) teardown_instance "$instance" ;;
    status) status_instance "$instance" ;;
  esac
done