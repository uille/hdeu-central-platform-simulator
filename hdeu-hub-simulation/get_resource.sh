#!/bin/bash
set -vx
exec 3<>/dev/tcp/"${1}"/"${2}" && echo -e "GET ${3} HTTP/1.1\r\nHost: ${1}\r\nConnection: close\r\n\r\n" >&3 && cat <&3 #| grep -q '200 OK'