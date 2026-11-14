# European Healthdata access simulator

This is an intergration project that provides a cordoned runtime (no connectivity with the message broker infrastructure) of the https://code.europa.eu/healthdataeu/healthdataeu-eu-dataset-catalogue central platform and a abcdesktop.io Helm Chart. Both systems use the same keycloak service for authentication. The central platform offers users the capability to issue data access applications, which an administrator can approve (currently view command line tools agains the API). The abcdesktop simulates a Secure Processing Environment where the data is injected after approval of the data access application.

## 1 install Podman 

## 2 install k3s

## build and deploy hdeu-hub-simulation/local-scenario.conf

in addition to getting the central platform services running (via podman-compose) minimal dataset metadata needs to be inserted into the central platform. See hdeu-hub-simulation/itb-valid-example-data/ for this.

## install the abcdesktop into the k3s cluster

abcdesktop/helm_chart has a modified version of the abcdesktop Chart which needs to be installed to the local k3s cluster. See abcdesktop/README.md for necessary steps


# key intergration failure point

Both of the services hinge on a single critical artifact, a certificate. The central platform nginx reverse proxied single entrypoint (healthdata-local.com:8092) is the TLS termination point with using a self signed certificate. They KeyCloak service that is included in the hdeu-hub-simulation/local-scenario.yml deployment is tucked behind this TLS termination. The most involved request arriving there are the OIDC token backchannel verification requests. Both the UI (hdeu-access) and the abcDesktop redirect the user first to the KeyCloak authenticaiton page, and after auhtenticaton get redirected with an opaque token back to their originating services (i.e. either the ui or abcdesktop) and at this point a handling endpoint receives the client carried token and initiates a token verification backchannel request against the KeyCloak. These request must have the self signed certificate properly configured as accepted certificates otherwise the authentication flow will fail. The certificate in question is the hdeu-hub-simulation/certs/healthdata-local.com.cert and it is signed to verify only 'healtdata-local.com' hosts. If the host name running this service bundle is changed to anything else, the certificate MUST BE CHANGED in-place to point to the new host name. The same certificate is hoisted to both of the backends (via difference mechanisms).

If the cert is changed, the hdeu-hub-simulator service bundle needs to be restarted (i.e. podman-compose down && podman compose up), and the Kubernetes secret must be recreated (See abcdesktop/README.md).


## KESKENERÄISIÄ

- hdeu-access ei vieläkään käynnisty oikeaan aikaan (keycloakin jälkeen)
- siirrä git repo jonnekkin pilveen
- email infran selvitys