I observed HTTP 503 responses on the ACM Digital Library service and traced it to a local application bottleneck: a single client (91.214.0.1) held 5 persistent connections to the `/dl/export` endpoint, each occupying a worker thread for 90 seconds. With only 3 max workers configured, the pool was exhausted, causing all other requests to fail.

I decided to increase `MAX_WORKERS` from 3 to 10 and restart the service, after escalating to ACM with three options (increase workers, rate-limit the client, or separate worker pools). ACM approved Option A and deferred access control changes.

I verified both HTTP and HTTPS endpoints returned 200 after the restart. Routing was confirmed normal throughout — this was purely an application-level resource exhaustion issue, not a network fault.