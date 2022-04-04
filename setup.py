import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name="pixivd",
    version="3.0",
    author="KK",
    author_email="bebound@gmail.com",
    description="A simple tool to download illustrations from Pixiv.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bebound/pixiv",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            'pixivd=pixivd.pixivd:main',
        ],
    },
    install_requires=[
        'requests>=2.4.3',
        'pyaes>=1.6.1',
        'docopt>=0.6.2',
        'tqdm',
        'PixivPy>=3.6.0',
    ],
    include_package_data=True,
)
