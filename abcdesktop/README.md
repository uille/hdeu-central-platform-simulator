# abcdesktop

This module contains a modified Helm Chart of the abcdesktop.io. It has been modified to integrate with the ../hdeu-hub-simulator/local-scenario.yml service composition included KeyCloak service. Each user must have an user accound created in the KeyCloak service and use that account to sign in into the the desktop. The desktops are meant to simulate a Secure Processing Environment where a dataset is inserted after approval of a data access request that has been processed though the central platform.

## Installation

export KUBECONFIG=~/.kube/config

### 1 add the self signed certificate as a Kubernetes secret

`kubectl create secret generic healthdata-local-ca-cert --from-file=healthdata-local.com.cert=../hdeu-hub-simulation/certs/healthdata-local.com.cert -n abcdesktop --dry-run=client -o yaml | kubectl apply -f -`

if the command was used to update while existing service was running then run

`kubectl rollout restart deployment pyos-od -n abcdesktop`

### 2 Create the user home folder mount root on the host

`mkdir /mnt/abcdesktop_volumes`

### 4 install/update the modified Helm Chart of abcDesktop

!Note! the `pyos.hostAliase[0].ip` in the following has to point a valid interface ip on the host. This is the route the abcDesktop 'pyos-od' pod will find the KeyClock services (when verifying OIDC token).

`helm upgrade --install my-abcdesktop ./helm_chart/ -n abcdesktop --create-namespace --set router.nodePort=30443 --set pyos.hostAliases[0].ip="192.168.0.79" --set pyos.hostAliases[0].hostnames[0]="healthdata-local.com"`

### 5 add the external OIDC KeyCloak identity provider config

```
kubectl create -n abcdesktop configmap abcdesktop-config --from-file=./config/od.config -o yaml --dry-run=client | kubectl apply -f -
kubectl rollout restart deployment pyos-od -n abcdesktop
kubectl logs -l name=pyos-od -n abcdesktop
```

the update may take a moment, but open a browser [at](http://healthdata-local.com:30443) and refresh until you see only the "Sign-in with HealthData Keycloak account" options for sign-in.

## Usage

The desktops have been configured to mount the */mnt/abcdesktop_volumes/{user_name}/* folder as the home folder in the destop. After the data access application has been approved for a user, an administrator will copy the data file into */mnt/abcdesktop_volumes/{user_name}/Desktop/* folder after which it is accessible to the user logged into the desktop. Check the copied file access rights, otherwise the user will not be able to do anything with it. Use rights can be restricted to read only using the standard linux file access rights.