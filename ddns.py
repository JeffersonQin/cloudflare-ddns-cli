import yaml
import requests
import os
import time
import sys
import json
import traceback
import ipaddress


root_dir = os.path.split(os.path.abspath(__file__))[0]
config_dir = os.path.join(root_dir, "config.yml")
log_dir = os.path.join(root_dir, "logs")
timestr = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
logfile_dir = os.path.join(log_dir, f"{timestr}.txt")

if "-p" not in sys.argv:
    os.makedirs(log_dir, exist_ok=True)
    log_stream = open(logfile_dir, "a+")
    sys.stdout = log_stream
    sys.stderr = log_stream

with open(config_dir, "r", encoding="utf8") as f:
    contents = f.read()
    config = yaml.load(contents, Loader=yaml.FullLoader)

my_ip = ""
X_AUTH_KEY = config["X_AUTH_KEY"]
ZONE_ID = config["ZONE_ID"]
EMAIL = config["EMAIL"]
DNS_RECORD_NAME = config["DNS_RECORD_NAME"]
WEBSITE_URL = config["WEBSITE_URL"]

v4 = config["TYPE"] == "v4"

type_str = "A" if v4 else "AAAA"

headers = {
    "X-Auth-Email": EMAIL,
    "X-Auth-Key": X_AUTH_KEY,
    "Content-Type": "application/json",
}


def get_time_str():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))


def get_ip_template(api_id):
    try:
        if api_id == 0:
            ip = requests.get(url="http://ip.3322.net/").text
        elif api_id == 1:
            ip = requests.get(url="http://myip.ipip.net/s").text
        elif api_id == 2:
            ip = requests.get(url="https://api.ip.sb/ip").text
        elif api_id == 3:
            ip = requests.get(url="http://ident.me/").text
        elif api_id == 4:
            ip = requests.get(url="http://ip.42.pl/raw").text
        ip = ip.strip()
        ipaddress.ip_address(ip)
        if v4:
            if type(ipaddress.ip_address(ip)) is not ipaddress.IPv4Address:
                raise Exception("IP IS NOT v4")
        else:
            if type(ipaddress.ip_address(ip)) is ipaddress.IPv4Address:
                raise Exception("IP IS NOT v6")
        return ip
    except:
        print(f"{get_time_str()} : GET IP FROM API {api_id} FAILED")
        traceback.print_exc()
        return None


while True:
    ip_success = False
    for i in range(5):
        new_ip = get_ip_template(i)
        if new_ip is not None:
            ip_success = True
            break
    if ip_success == False:
        print(f"{get_time_str()} : IP UPDATE ERROR")
        try:
            time.sleep(int(config["IP_FAIL_INTERVAL"]))
        except:
            print(f"{get_time_str()} : ERROR OCCURRED DURING SLEEP")
            traceback.print_exc()
        continue

    print(f"{get_time_str()} : IP : {new_ip}")

    if new_ip != my_ip or error_flag:
        print(f"{get_time_str()} : Start updating IP ...")
        my_ip = new_ip
        try:
            response = requests.get(
                url="https://api.cloudflare.com/client/v4/zones/"
                + ZONE_ID
                + "/dns_records",
                headers=headers,
            )
            res = json.loads(response.text)
            result_arr = res["result"]
            site_id = ""
            for result in result_arr:
                if result["type"] == type_str:
                    if str(result["name"]) == WEBSITE_URL:
                        site_id = result["id"]
                        break
            response = requests.put(
                url="https://api.cloudflare.com/client/v4/zones/"
                + ZONE_ID
                + "/dns_records/"
                + str(site_id),
                headers=headers,
                data='{"type":"'
                + type_str
                + '","name":"'
                + DNS_RECORD_NAME
                + '","content":"'
                + my_ip
                + '","ttl":1,"proxied":false}',
            )
            res = json.loads(response.text)
            if res["success"]:
                print(f"{get_time_str()} : UPLOAD SUCCESS : {my_ip}")
                error_flag = False
            else:
                print(f"{get_time_str()} : UPLOAD FAILED")
                print(f"SERVER RESULT: {res}")
                error_flag = True
        except Exception as e:
            print(f"{get_time_str()} : ERROR OCCURRED")
            traceback.print_exc()
            error_flag = True

    if not error_flag:
        try:
            time.sleep(int(config["INTERVAL"]))
        except:
            print(f"{get_time_str()} : ERROR OCCURRED DURING SLEEP")
            traceback.print_exc()
