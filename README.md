# European Healthdata access simulator

This is an intergration project that provides a cordoned runtime (no connectivity with the message broker infrastructure) of the https://code.europa.eu/healthdataeu/healthdataeu-eu-dataset-catalogue central platform and a abcdesktop.io Helm Chart. Both systems use the same keycloak service for authentication. The central platform offers users the capability to issue data access applications, which an administrator can approve (currently view command line tools agains the API). The abcdesktop simulates a Secure Processing Environment where the data is injected after approval of the data access application.

## Required software on the host running this

- Podman 
- k3s
- Helm
- mongosh

Additionally either the host must be named 'healthdata-local.com' or alised from localhost as such (in /etc/hosts). The 'healthdata-local.com' hostname is peppered into the myriad configuration files and modifying it is a task unto itself.

## build and deploy hdeu-hub-simulation/local-scenario.conf

run in /hdeu/hdeu-hub-simulation/

first build
```CONTAINERS_CONF=./containers.conf podman-compose -f local-scenario.yml build```
then run
```CONTAINERS_CONF=./containers.conf podman-compose -f local-scenario.yml up -d```

check the hdeu-access logs, it still has problem of starting too early and failing

```podman logs hdeu-access```
if it says "Error in Keycloak JWKS fetching or processing [...] ==Shutting down service==" the rerun
```CONTAINERS_CONF=./containers.conf podman-compose -f local-scenario.yml up -d```

The UI will be available [here](https://healthdata-local.com:8092/)

NOTE! the CONTAINERS_CONF=./containers.conf is necessary because Podman-compose seems to use the hosts /etc/hosts as the baseline when constructing the containers /etc/hosts. This is a problem because if the host /etc/hosts contains

```
127.0.0.1 healthdata-local.com
```

The intercontainer routing will fail. Because the ngingx container is aliases as 'healthdata-local-com' so that container service can request OIDC token verification via the same endpoint. If they start routing to their localhost, it's a bust. 


## Minimal dataset

In addition to getting the central platform services running (via podman-compose) minimal dataset metadata needs to be inserted into the central platform. See hdeu-hub-simulation/itb-valid-example-data/ for this.

## install the abcdesktop into the k3s cluster

abcdesktop/helm_chart has a modified version of the abcdesktop Chart which needs to be installed to the local k3s cluster. See abcdesktop/README.md for necessary steps


# key intergration failure point

Both of the services hinge on a single critical artifact, a certificate. The central platform nginx reverse proxied single entrypoint (healthdata-local.com:8092) is the TLS termination point with using a self signed certificate. They KeyCloak service that is included in the hdeu-hub-simulation/local-scenario.yml deployment is tucked behind this TLS termination. The most involved request arriving there are the OIDC token backchannel verification requests. Both the UI (hdeu-access) and the abcDesktop redirect the user first to the KeyCloak authenticaiton page, and after auhtenticaton get redirected with an opaque token back to their originating services (i.e. either the ui or abcdesktop) and at this point a handling endpoint receives the client carried token and initiates a token verification backchannel request against the KeyCloak. These request must have the self signed certificate properly configured as accepted certificates otherwise the authentication flow will fail. The certificate in question is the hdeu-hub-simulation/certs/healthdata-local.com.cert and it is signed to verify only 'healtdata-local.com' hosts. If the host name running this service bundle is changed to anything else, the certificate MUST BE CHANGED in-place to point to the new host name. The same certificate is hoisted to both of the backends (via difference mechanisms).

If the cert is changed, the hdeu-hub-simulator service bundle needs to be restarted (i.e. podman-compose down && podman compose up), and the Kubernetes secret must be recreated (See abcdesktop/README.md).

## Needs fixing

- admin/operator needs to be informed when application created
- hdeu-access still won't cleanly synchronize with keycloak ready up (hdeu-access start before keycloak is ready and fails when requesting JWKS from it)
- email sending needs to be enabled and email infrastructure configure (SMPT server)
- Keyclock needs to be disabled from dev mode (into production mode)
- administrative interface (keycloak admin page, abcdekstop admin page) need to be hidden (into local network accesses only)

## Use case flow

# Add user credentials

```
podman exec -ti keycloak /bin/bash

/opt/keycloak/bin/kcadm.sh config credential --server http://localhost:8080/keycloak --realm master --user admin --password admin

/opt/keycloak/bin/kcadm.sh create users \
  -r healthdata \
  -s username=testuser \
  -s enabled=true \
  -s email=testuser@example.com \
  -s firstName=Test \
  -s lastName=User

/opt/keycloak/bin/kcadm.sh set-password \
  -r healthdata \
  --username testuser \
  --new-password 'MySecretPassword123' \
  --temporary

/opt/keycloak/bin/kcadm.sh add-roles \
  -r healthdata \
  --uusername testuser \
  --rolename default-roles-healthdata
```
# User logs in and creates a data access application

# User translates and submits the application

Currently there is no notification to admin/operator when this happens, needs some patching.

# administrator/operator approves the application

See hdeu-hub-simulation/application-state-flow-scripts/README.md

# administrator/operator injects the dataset file onto the users desktop

The abcdesktop will mount users home folder from /mnt/abcdesktop_volumes/{user_name}. Drop the data file at /mnt/abcdesktop_volumes/{user_name}/Desktop/your_file_here, it will become visible to the user. Check file access rights. See /hdeu/abcdesktop/README.md
