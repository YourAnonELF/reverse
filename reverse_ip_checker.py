import argparse
import ipaddress
import json
import socket
from typing import Dict, List, Optional, TypedDict


class ReverseLookupResult(TypedDict):
    success: bool
    hostnames: List[str]
    addresses: List[str]
    error: Optional[str]


class ForwardLookupResult(TypedDict):
    success: bool
    addresses: List[str]
    error: Optional[str]


class CheckResult(TypedDict):
    ip: str
    reverse: ReverseLookupResult
    domain: Optional[str]
    forward: Optional[ForwardLookupResult]
    forward_matches_ip: Optional[bool]
    reverse_matches_domain: Optional[bool]


def validate_ip(ip: str) -> str:
    ipaddress.ip_address(ip)
    return ip


def reverse_lookup(ip: str) -> ReverseLookupResult:
    validate_ip(ip)
    try:
        hostname, aliases, addresses = socket.gethostbyaddr(ip)
        hostnames: List[str] = [hostname] + [alias for alias in aliases if alias != hostname]
        return {
            "success": True,
            "hostnames": hostnames,
            "addresses": addresses,
            "error": None,
        }
    except (socket.herror, socket.gaierror, OSError) as exc:
        return {
            "success": False,
            "hostnames": [],
            "addresses": [],
            "error": str(exc),
        }


def forward_lookup(domain: str) -> ForwardLookupResult:
    try:
        _, _, addresses = socket.gethostbyname_ex(domain)
        return {
            "success": True,
            "addresses": addresses,
            "error": None,
        }
    except (socket.gaierror, OSError) as exc:
        return {
            "success": False,
            "addresses": [],
            "error": str(exc),
        }


def check_reverse_ip_domain(ip: str, domain: Optional[str] = None) -> CheckResult:
    reverse = reverse_lookup(ip)
    result: CheckResult = {
        "ip": ip,
        "reverse": reverse,
        "domain": domain,
        "forward": None,
        "forward_matches_ip": None,
        "reverse_matches_domain": None,
    }

    if domain:
        forward = forward_lookup(domain)
        reverse_names = (
            {name.lower().rstrip(".") for name in reverse["hostnames"]}
            if reverse["success"]
            else set()
        )
        domain_normalized = domain.lower().rstrip(".")

        result["forward"] = forward
        result["forward_matches_ip"] = ip in forward["addresses"] if forward["success"] else False
        result["reverse_matches_domain"] = (
            domain_normalized in reverse_names if reverse["success"] else False
        )

    return result


def _print_check_result_terminal(result: CheckResult) -> None:
    print(f"IP: {result['ip']}")

    reverse = result["reverse"]
    if reverse["success"]:
        print("Reverse lookup: success")
        print("Hostnames:")
        for host in reverse["hostnames"]:
            print(f"- {host}")
    else:
        print("Reverse lookup: failed")
        print(f"Error: {reverse['error']}")

    if result["domain"]:
        print(f"Domain: {result['domain']}")
        forward = result["forward"]
        if forward and forward["success"]:
            print("Forward lookup: success")
            print("Resolved IPs:")
            for addr in forward["addresses"]:
                print(f"- {addr}")
        else:
            print("Forward lookup: failed")
            error_message = forward["error"] if forward is not None else "unknown error"
            print(f"Error: {error_message}")

        print(f"Forward matches IP: {result['forward_matches_ip']}")
        print(f"Reverse matches domain: {result['reverse_matches_domain']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reverse-IP domain checker (terminal tool)")
    parser.add_argument("--ip", required=True, help="IP address to check")
    parser.add_argument("--domain", help="Optional domain to verify against the IP")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of plain text")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        validate_ip(args.ip)
    except ValueError:
        raise SystemExit("Invalid IP address")

    result = check_reverse_ip_domain(args.ip, args.domain)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_check_result_terminal(result)


if __name__ == "__main__":
    main()
