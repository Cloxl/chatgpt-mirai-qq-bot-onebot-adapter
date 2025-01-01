from setuptools import setup, find_packages

setup(
    name="chatgpt-mirai-qq-bot-onebot-adapter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiocqhttp",
    ],
    author="Cloxl",
    author_email="cloxl2017@outlook.at",
    description="OneBot adapter for lss233/chatgpt-mirai-qq-bot",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cloxl/chatgpt-mirai-qq-bot-onebot-adapter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
