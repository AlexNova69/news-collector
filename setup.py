from setuptools import setup, find_packages
import os

# Чтение описания из README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="news-collector",
    version="1.0.0",
    description="Автоматический сборщик новостей с AI-обработкой",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="News Collector Team",
    author_email="example@example.com",
    packages=find_packages(),
    py_modules=['news_collector'],
    install_requires=[
        'requests>=2.31.0',
        'beautifulsoup4>=4.12.2',
        'schedule>=1.2.0',
        'lxml>=4.9.3',
        'urllib3>=2.0.7'
    ],
    entry_points={
        'console_scripts': [
            'news-collector=news_collector:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Utilities',
    ],
    python_requires='>=3.7',
    keywords='news, collector, web scraping, ai, automation',
)