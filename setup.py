from setuptools import find_packages, setup

import versioneer

with open("requirements.txt", "rt") as fp:
    install_requires = [
        line for line in fp.read().splitlines()
        if line and not line.startswith("#")
    ]


setup(
    name="lightpath",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="BSD",
    author="SLAC National Accelerator Laboratory",
    packages=find_packages(),
    package_data={
        "lightpath": ["ui/*.ui"],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'lightpath = lightpath.main:entrypoint',
        ],
        "happi.containers": ["lightpath = lightpath.happi.containers"],
    },
    install_requires=install_requires,
    python_requires=">=3.6",
)
