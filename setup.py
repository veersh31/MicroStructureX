"""
Setup script for MicroStructureX package.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="microstructurex",
    version="1.0.0",
    author="MicroStructureX Team",
    description="Production-grade Market Microstructure Simulator with Limit Order Book",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/microstructurex",
    packages=find_packages(exclude=["tests*", "notebooks*", "scripts*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "pydantic>=2.5.0",
        "python-multipart>=0.0.6",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "pyarrow>=12.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "ruff>=0.1.0",
        ],
        "viz": [
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
            "plotly>=5.17.0",
            "jupyter>=1.0.0",
            "jupyterlab>=4.0.0",
        ],
        "perf": [
            "numba>=0.58.0",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "microstructurex-server=src.api.server:main",
            "microstructurex-benchmark=scripts.benchmark_performance:main",
        ],
    },
)
