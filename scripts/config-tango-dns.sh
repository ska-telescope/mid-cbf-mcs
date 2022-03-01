#!/bin/bash

kubectl get services -n $1 | while read -r line;
do
    svc_split=($line)
    if [ "${svc_split[1]}" = "LoadBalancer" ]; then
        host_name="${svc_split[0]%"-external"}.$1.svc.$2"
        echo "${svc_split[3]} $host_name"
        sudo sed -i -e "/.*$host_name.*/d" -e "\$a${svc_split[3]} $host_name" /etc/hosts    #sudo sed -i "s/.*$host_name.*//" /etc/hosts
        #sudo echo "${svc_split[3]} $host_name" >> /etc/hosts
    fi
done