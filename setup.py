import setuptools

version_namespace = {}
with open("gui4us/version.py") as f:
    exec(f.read(), version_namespace)


setuptools.setup(
    name="gui4us",
    version=version_namespace["__version__"],
    author="us4us Ltd.",
    author_email="support@us4us.eu",
    description="GUI 4 ultrasound",
    long_description="GUI 4 ultrasound",
    long_description_content_type="text/markdown",
    url="https://us4us.eu",
    packages=setuptools.find_packages(exclude=[]),
    classifiers=[
        "Development Status :: 1 - Planning",

        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",

        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Medical Science Apps."
    ],
    entry_points={
        "console_scripts": [
            "gui4us = gui4us:main"
        ]
    },
    install_requires=[
        "arrus>=0.5.11",
        "pyyaml",
        "PyQt5",
        "matplotlib>=3.6.2"
    ],
    python_requires='>=3.8'
)