from __future__ import annotations

from uuid import uuid4
from importlib.metadata import version


def _marker_labels() -> dict[str, str]:
    # String testcontainersVersion = TESTCONTAINERS_VERSION == null ? "unspecified" : TESTCONTAINERS_VERSION;
    # Map<String, String> labels = new HashMap<>();
    # labels.put(TESTCONTAINERS_LABEL, "true");
    # labels.put(TESTCONTAINERS_LANG_LABEL, "java");
    # labels.put(TESTCONTAINERS_VERSION_LABEL, testcontainersVersion);
    # return Collections.unmodifiableMap(labels);
    testcontainers_version = "unspecified" if TESTCONTAINERS_VERSION is None else TESTCONTAINERS_VERSION
    return {
        TESTCONTAINERS_LABEL: "true",
        TESTCONTAINERS_LANG_LABEL: "python",
        TESTCONTAINERS_VERSION_LABEL: testcontainers_version,
    }


TESTCONTAINERS_LABEL = "org.testcontainers"
TESTCONTAINERS_SESSION_ID_LABEL = TESTCONTAINERS_LABEL + ".sessionId"
TESTCONTAINERS_LANG_LABEL = TESTCONTAINERS_LABEL + ".lang"
TESTCONTAINERS_VERSION_LABEL = TESTCONTAINERS_LABEL + ".version"
SESSION_ID = uuid4()
TESTCONTAINERS_VERSION = version("testcontainers")
DEFAULT_LABELS = _marker_labels()


class DockerClientFactory:
    @staticmethod
    def lazy_client() -> DockerClient:
        pass
