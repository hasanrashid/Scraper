import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Scrape-Books", # Replace with your own username
    version="0.0.1",
    author="soaad",
    author_email="hasan.j.rashid@gmail.com",
    description="Python package to scrape Bengali PDFs from specific sites",
    url="https://github.com/hasanjrashid",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)