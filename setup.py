import setuptools

setuptools.setup(
    name="gui4us",
    version="0.0.1",
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
    install_requires=[
        "arrus>=0.5.11",
        "pyyaml",
        "PyQt5"
    ],
    python_requires='>=3.8'
)