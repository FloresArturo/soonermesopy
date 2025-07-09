from setuptools import setup, find_packages

setup(
    name="soonermesopy",
    version="0.1.0",
    description="Tools to download data from the Oklahoma Mesonet",
    author="Arturo J. Flores",
    author_email="artuflo@okstate.edu",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "requests",
        "tqdm"
    ],
    python_requires=">=3.8",
)
