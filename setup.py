from setuptools import setup
import os
import re

if os.environ.get("CI_COMMIT_TAG"):
    version = os.environ["CI_COMMIT_TAG"]
    if version.startswith("v"):
        version = version[1:]
        if not re.search(r"^\d+\.\d+\.\d+$", version):
            raise AttributeError(
                "given CI_COMMIT_TAG {} incorrect format. It must be vX.Y.Z or X.Y.Z format".format(
                    os.environ["CI_COMMIT_TAG"]
                )
            )
elif os.environ.get("CI_JOB_ID"):
    version = os.environ["CI_JOB_ID"]
else:
    version = None

setup(
    zip_safe=True,
    name="pytijo_api_client",
    version=version,
    author="Jon Castro",
    author_email="jon@tijo.io",
    packages=["pytijo_api_client"],
    description="Tijo API client",
    license="LICENSE",
    install_requires=["requests"],
)
