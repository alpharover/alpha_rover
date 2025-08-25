#!/usr/bin/env python3
import argparse
import json
import sys
import time
from urllib import request, parse, error


DEFAULT_FRONT_IP = "192.168.1.200"
DEFAULT_REAR_IP = "192.168.1.201"


def http_get_json(url, timeout=2.0):
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
            return json.loads(data.decode("utf-8", errors="ignore"))
    except Exception as e:
        raise RuntimeError(f"GET {url} failed: {e}")


def http_post_form(url, fields, timeout=3.0):
    data = parse.urlencode(fields).encode()
    req = request.Request(url, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            # We don't care about body; a 200 means CGI ran
            resp.read()
            return True
    except error.HTTPError as e:
        # Some firmwares redirect or return 500 even when accepted; treat 2xx/3xx as success
        if 200 <= e.code < 400:
            return True
        raise RuntimeError(f"POST {url} failed: HTTP {e.code}")
    except Exception as e:
        raise RuntimeError(f"POST {url} failed: {e}")


def get_setting(ip):
    return http_get_json(f"http://{ip}/setting_data.json")


def get_diag(ip):
    return http_get_json(f"http://{ip}/diag_data.json")


def set_op_mode(ip, mode_value):
    # Fetch current settings, modify OpM, POST back to firmware handler.
    settings = get_setting(ip)
    settings["OpM"] = str(mode_value)
    # The main form button name for network/op mode group is 'save_param'
    fields = {k: v for k, v in settings.items()}
    fields["save_param"] = "Save"
    # Newer firmwares accept POST to the HTML page path; try that first.
    try:
        http_post_form(f"http://{ip}/Parameter_Setting.html", fields)
        return
    except Exception:
        pass
    # Fallback: some devices may expose a CGI handler
    http_post_form(f"http://{ip}/cgi-bin/param_setting.cgi", fields)


def summarize_status(ip):
    out = {
        "ip": ip,
        "op_mode": None,
        "rpm": None,
        "laser": None,
        "temp_c": None,
    }
    try:
        s = get_setting(ip)
        d = get_diag(ip)
        out["op_mode"] = s.get("OpM")
        out["rpm"] = d.get("rpm")
        out["laser"] = d.get("laser_sts")
        out["temp_c"] = d.get("temp")
    except Exception as e:
        out["error"] = str(e)
    return out


def parse_args(argv):
    p = argparse.ArgumentParser(prog="oak lidar", description="Control RoboSense AIRY LiDAR operation mode")
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--front-ip", default=DEFAULT_FRONT_IP)
    common.add_argument("--rear-ip", default=DEFAULT_REAR_IP)
    common.add_argument("--lidar", choices=["front", "rear", "both"], default="both")

    sub.add_parser("status", parents=[common], help="Show status (mode, rpm, laser)")
    sub.add_parser("standby", parents=[common], help="Set Operation Mode to Standby (stop motor/laser)")
    sub.add_parser("run", parents=[common], help="Set Operation Mode to High-Performance (enable)")

    return p.parse_args(argv)


def targets(args):
    if args.lidar == "front":
        return [args.front_ip]
    if args.lidar == "rear":
        return [args.rear_ip]
    return [args.front_ip, args.rear_ip]


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    ips = targets(args)

    if args.cmd == "status":
        any_err = False
        for ip in ips:
            info = summarize_status(ip)
            if "error" in info:
                any_err = True
                print(f"{ip}: ERROR: {info['error']}")
            else:
                mode = {"0": "Standby", "1": "High-Performance"}.get(str(info["op_mode"]), str(info["op_mode"]))
                print(f"{ip}: mode={mode} rpm={info['rpm']} laser={info['laser']} temp_c={info['temp_c']}")
        return 1 if any_err else 0

    if args.cmd in ("standby", "run"):
        mode_val = 0 if args.cmd == "standby" else 1
        for ip in ips:
            try:
                print(f"{ip}: setting OpM={mode_val} ...", flush=True)
                set_op_mode(ip, mode_val)
            except Exception as e:
                print(f"{ip}: FAILED: {e}")
                return 2
        # Give firmware a moment to apply
        time.sleep(1.0)
        # Verify
        ok = True
        for ip in ips:
            info = summarize_status(ip)
            desired = str(mode_val)
            if "error" in info or str(info.get("op_mode")) != desired:
                print(f"{ip}: Verify failed: {info}")
                ok = False
            else:
                mode = {"0": "Standby", "1": "High-Performance"}.get(desired, desired)
                print(f"{ip}: OK → {mode}; rpm={info['rpm']} laser={info['laser']}")
        return 0 if ok else 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
