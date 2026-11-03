from dataclasses import dataclass
from logging import getLogger
from os import environ
from pathlib import Path
from typing import Any, ClassVar, overload

import jproperties

from testcontainers.utility.docker_image_name import DockerImageName

_PROPERTIES_FILE_NAME = "testcontainers.properties"
_USER_CONFIG_FILE = Path.home() / f".{_PROPERTIES_FILE_NAME}"
_AMBASSADOR_IMAGE = "richnorth/ambassador"
_SOCAT_IMAGE = "alpine/socat"
_VNC_RECORDER_IMAGE = "testcontainers/vnc-recorder"
_COMPOSE_IMAGE = "docker/compose"
_ALPINE_IMAGE = "alpine"
_RYUK_IMAGE = "testcontainers/ryuk"
_KAFKA_IMAGE = "confluentinc/cp-kafka"
_PULSAR_IMAGE = "apachepulsar/pulsar"
_LOCALSTACK_IMAGE = "localstack/localstack"
_SSHD_IMAGE = "testcontainers/sshd"
_ORACLE_IMAGE = "gvenzl/oracle-xe"
_CONTAINER_MAPPING = {
    DockerImageName.parse(_AMBASSADOR_IMAGE): "ambassador.container.image",
    DockerImageName.parse(_SOCAT_IMAGE): "socat.container.image",
    DockerImageName.parse(_VNC_RECORDER_IMAGE): "vncrecorder.container.image",
    DockerImageName.parse(_COMPOSE_IMAGE): "compose.container.image",
    DockerImageName.parse(_ALPINE_IMAGE): "tinyimage.container.image",
    DockerImageName.parse(_RYUK_IMAGE): "ryuk.container.image",
    DockerImageName.parse(_KAFKA_IMAGE): "kafka.container.image",
    DockerImageName.parse(_PULSAR_IMAGE): "pulsar.container.image",
    DockerImageName.parse(_LOCALSTACK_IMAGE): "localstack.container.image",
    DockerImageName.parse(_SSHD_IMAGE): "sshd.container.image",
    DockerImageName.parse(_ORACLE_IMAGE): "oracle.container.image",
}

log = getLogger(__name__)


@dataclass
class TestcontainersConfiguration:
    _INSTANCE: ClassVar[TestcontainersConfiguration | None] = None
    _user_properties: dict[str, Any]
    _classpath_properties: dict[str, Any]
    _environment: dict[str, str]

    @classmethod
    def get_instance(cls) -> TestcontainersConfiguration:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls._load_properties()
        assert cls._INSTANCE is not None
        return cls._INSTANCE

    @staticmethod
    def _read_classpath_properties() -> dict[str, Any]:
        return {}  # todo

    def is_ryuk_privileged(self) -> bool:
        return parse_boolean(self.get_env_var_or_user_property("ryuk.container.privileged", "true"))

    def get_ryuk_timeout(self) -> int:
        return int(self.get_env_var_or_user_property("ryuk.container.timeout", "30"))

    def is_disable_checks(self) -> bool:
        return parse_boolean(self.get_env_var_or_user_property("checks.disable", "false"))

    def environment_supports_reuse(self) -> bool:
        return parse_boolean(self.get_env_var_or_user_property("testcontainers.reuse.enabled", "false"))

    def get_docker_client_strategy_class_name(self) -> str | None:
        prefixed_env_var_strategy = self._environment.get("TESTCONTAINERS_DOCKER_CLIENT_STRATEGY")
        if prefixed_env_var_strategy is not None:
            return prefixed_env_var_strategy
        return self.get_env_var_or_user_property("docker.client.strategy", None)

    def get_image_pull_pause_timeout(self) -> int:
        return int(self.get_env_var_or_user_property("pull.pause.timeout", "30"))

    def get_image_pull_timeout(self) -> int:
        return int(self.get_env_var_or_user_property("pull.timeout", "120"))

    def get_image_substitutor_class_name(self) -> str | None:
        return self.get_env_var_or_user_property("image.substitutor", None)

    def get_image_pull_policy(self) -> str | None:
        return self.get_env_var_or_user_property("pull.policy", None)

    def get_client_ping_timeout(self) -> int:
        return int(self.get_env_var_or_user_property("client.ping.timeout", "10"))

    def _get_configurable(
        self,
        property_name: str,
        default_value: str | None,
        *properties_sources: dict[str, Any],
    ) -> str | None:
        env_var_name = property_name.replace(".", "_").upper()
        if not env_var_name.startswith("TESTCONTAINERS_") and not env_var_name.startswith("DOCKER_"):
            env_var_name = "TESTCONTAINERS_" + env_var_name

        if env_var_name in self._environment:
            value = self._environment.get(env_var_name)
            if value is not None and len(value) != 0:
                return value

        for properties in properties_sources:
            if properties.get(property_name) is not None:
                return properties.get(property_name)

        return default_value

    @overload
    def get_env_var_or_user_property(self, property_name: str, default_value: None) -> None: ...

    @overload
    def get_env_var_or_user_property(self, property_name: str, default_value: str) -> str: ...

    def get_env_var_or_user_property(self, property_name: str, default_value: str | None) -> str | None:
        return self._get_configurable(property_name, default_value, self._user_properties)

    @overload
    def get_env_var_or_property(self, property_name: str, default_value: None) -> None: ...

    @overload
    def get_env_var_or_property(self, property_name: str, default_value: str) -> str: ...

    def get_env_var_or_property(self, property_name: str, default_value: str | None) -> str | None:
        return self._get_configurable(property_name, default_value, self._user_properties, self._classpath_properties)

    @overload
    def get_user_property(self, property_name: str, default_value: None) -> None: ...

    @overload
    def get_user_property(self, property_name: str, default_value: str) -> str: ...

    def get_user_property(self, property_name: str, default_value: str | None) -> str | None:
        self._user_properties.get(property_name, default_value)

    def update_user_config(self, prop: str, value: str) -> bool:
        try:
            if value == self._user_properties.get(prop):
                return False

            with _USER_CONFIG_FILE.open("w") as f:
                jproperties.Properties(self._user_properties).store(f)

            self._user_properties[prop] = value
            return True
        except Exception:
            log.debug("Can't store environment property %s in %s", prop, _USER_CONFIG_FILE, exc_info=True)
            return False

    @classmethod
    def _load_properties(cls) -> TestcontainersConfiguration:
        return TestcontainersConfiguration(
            _user_properties=cls._read_properties(_USER_CONFIG_FILE),
            _classpath_properties=cls._read_classpath_properties(),
            _environment={**environ},
        )

    @staticmethod
    def _read_properties(path: Path) -> dict[str, Any]:
        p = jproperties.Properties()
        p.load(path.read_text())
        return {**p}

    def get_configured_substitute_image(self, original: DockerImageName) -> DockerImageName:
        for substitutable_image, property_name in _CONTAINER_MAPPING.items():
            if original.is_compatible_with(substitutable_image):
                if property_name is None:
                    continue
                property_value = self.get_env_var_or_user_property(property_name, None)
                if property_value is None:
                    continue
                substitutable = DockerImageName.parse(str(property_value).strip())
                return substitutable.as_compatible_substitute_for_name(original)
        return original


def parse_boolean(maybe_boolean: str) -> bool:
    return str(maybe_boolean).lower() == "true"
