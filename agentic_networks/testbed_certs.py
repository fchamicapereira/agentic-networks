"""Mint the throwaway TLS material the knowledge-plane testbed needs.

The emulated ACM web server speaks HTTPS, so the client hosts need a certificate they
trust — which means a CA, and the experiment installs that CA into the container's trust
store. Shipping a fixed CA in the repository would mean publishing its private key, and a
CA private key that anyone can read is a CA that anyone can mint trusted certificates
with. Instead the whole chain is generated per run into a temporary directory and thrown
away with it.

Certificates are produced with the ``openssl`` CLI rather than a library so that no
dependency beyond the base image is needed; ``openssl`` is installed by the Dockerfile
and by tools/setup.sh.
"""

import subprocess
import tempfile

from dataclasses import dataclass
from pathlib import Path

# Long enough that a run can never outlive its certificates, short enough that material
# left behind in a temp directory is not useful later.
_VALIDITY_DAYS = 30
_KEY_BITS = 2048


@dataclass(frozen=True)
class TestbedCerts:
    """Filesystem locations of one run's generated TLS material."""

    directory: Path
    ca_cert: Path
    ca_key: Path
    server_cert: Path
    server_key: Path


def _openssl(*args: str) -> None:
    """Run an openssl subcommand, surfacing its stderr if it fails."""
    result = subprocess.run(["openssl", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"openssl {' '.join(args)} failed:\n{result.stderr.strip()}")


def generate(hostname: str, ip: str, dest_dir: Path | None = None, logger=None) -> TestbedCerts:
    """Generate a self-signed CA and a server certificate for ``hostname``/``ip``.

    The server certificate carries both names in its SAN, because clients reach the
    emulated server by name (through the testbed's DNS) and by address (when an agent is
    bypassing DNS to isolate a fault).
    """
    directory = Path(dest_dir) if dest_dir else Path(tempfile.mkdtemp(prefix="kp-testbed-certs-"))
    directory.mkdir(parents=True, exist_ok=True)

    ca_cert = directory / "testbed-ca.crt"
    ca_key = directory / "testbed-ca.key"
    server_cert = directory / "server.crt"
    server_key = directory / "server.key"
    csr = directory / "server.csr"
    ext = directory / "server.ext"

    _openssl(
        "req", "-x509", "-nodes",
        "-newkey", f"rsa:{_KEY_BITS}",
        "-keyout", str(ca_key),
        "-out", str(ca_cert),
        "-days", str(_VALIDITY_DAYS),
        "-subj", "/CN=Testbed CA/O=Network Testbed",
        "-addext", "basicConstraints=critical,CA:TRUE",
    )

    _openssl(
        "req", "-nodes",
        "-newkey", f"rsa:{_KEY_BITS}",
        "-keyout", str(server_key),
        "-out", str(csr),
        "-subj", f"/CN={hostname}/O=ACM Digital Library",
    )

    # SAN must be attached when the CA signs the CSR: openssl does not carry extensions
    # over from the request by default, and a certificate without a SAN is rejected
    # outright by modern clients even when the CN matches.
    ext.write_text(f"basicConstraints=CA:FALSE\nsubjectAltName=DNS:{hostname},IP:{ip}\n")

    _openssl(
        "x509", "-req",
        "-in", str(csr),
        "-CA", str(ca_cert),
        "-CAkey", str(ca_key),
        "-CAcreateserial",
        "-out", str(server_cert),
        "-days", str(_VALIDITY_DAYS),
        "-extfile", str(ext),
    )

    csr.unlink(missing_ok=True)
    ext.unlink(missing_ok=True)

    # The server runs as a different user context than the orchestrator in some setups;
    # the key must stay readable by it but not by the world.
    ca_key.chmod(0o600)
    server_key.chmod(0o644)

    if logger:
        logger.info("Generated testbed TLS material for %s (%s) in %s", hostname, ip, directory)

    return TestbedCerts(
        directory=directory,
        ca_cert=ca_cert,
        ca_key=ca_key,
        server_cert=server_cert,
        server_key=server_key,
    )
