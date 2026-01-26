"""
Setup script for MediGuard package.
"""

from setuptools import setup, find_packages

# Read requirements from requirements.txt
def read_requirements():
    with open("requirements.txt", "r") as f:
        requirements = []
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith("#"):
                requirements.append(line)
        return requirements

setup(
    name="mediaguard",
    version="1.0.0",
    description="Multi-Agent Clinical Compliance Orchestrator",
    author="MediGuard Team",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "mediguard=mediaguard.cli:cli",
        ],
    },
)
