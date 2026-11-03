from testcontainers.utility.docker_image_name import DockerImageName


def test_docker_image_name():
    DockerImageName.parse("hello")
