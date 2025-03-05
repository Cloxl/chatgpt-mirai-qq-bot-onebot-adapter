from setuptools import setup, find_packages
import io
import os

version = os.environ.get('RELEASE_VERSION', '0.1.0').lstrip('v')

setup(
    name="chatgpt-mirai-qq-bot-onebot-adapter",
    version=version,
    packages=find_packages(),
    install_requires=[
        "aiocqhttp[all]>=1.4.4",
    ],
    entry_points={
        'chatgpt_mirai.plugins': [
            'im_onebot_adapters = im_onebot_adapters:OneBotAdapterPlugin'
        ]
    },
    author="Cloxl",
    author_email="cloxl2017@outlook.at",

    description="OneBot adapter for lss233/chatgpt-mirai-qq-bot",
    long_description=io.open("README.md", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cloxl/chatgpt-mirai-qq-bot-onebot-adapter",
    classifiers=[
        "Programming Language :: Python :: 3",
        'License :: OSI Approved :: GNU Affero General Public License v3',
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/cloxl/chatgpt-mirai-qq-bot-onebot-adapter/issues",
        "Documentation": "https://oa-docs.cloxl.com",
        "Source Code": "https://github.com/cloxl/chatgpt-mirai-qq-bot-onebot-adapter",
    },
    python_requires=">=3.8",
)
