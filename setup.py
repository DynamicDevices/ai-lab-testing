"""
Setup script for Lab Testing MCP Server
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read version from version module
try:
    from lab_testing.version import __version__
except ImportError:
    __version__ = "0.1.0"

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="ai-lab-testing",
    version=__version__,
    description=(
        "MCP server for remote embedded hardware testing. "
        "Making remote embedded hardware development easy and accessible for engineers. "
        "Provides intelligent tooling with helpful guidance, best practices, and automated workflows."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alex J Lennon",
    author_email="ajlennon@dynamicdevices.co.uk",
    maintainer="Alex J Lennon",
    maintainer_email="ajlennon@dynamicdevices.co.uk",
    license="GPL-3.0-or-later",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "mcp>=1.0.0",
        "pydantic>=2.0.0",
        "requests>=2.28.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mcp-lab-testing=lab_testing.server:main",
        ],
    },
)
