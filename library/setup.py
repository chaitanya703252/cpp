"""Setup configuration for leave-manager-nci package."""

from setuptools import setup, find_packages

setup(
    name="leave-manager-nci",
    version="1.0.0",
    description="Employee Leave Management Library for LeaveFlow",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Lakshmi Chaitanya",
    author_email="x25171216@student.ncirl.ie",
    url="https://github.com/chaitanya703252/cpp",
    packages=find_packages(),
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
