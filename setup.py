from setuptools import setup, find_packages

setup(
    name="rag-vector-doc-claude",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.103.1",
        "uvicorn>=0.23.2",
        "pydantic>=2.3.0",
        "qdrant-client>=1.5.4",
        "langchain>=0.0.267",
        "openai>=0.28.0",
        "transformers>=4.33.2",
        "sentence-transformers>=2.2.2",
        "torch>=2.0.1",
        "pypdf>=3.15.1",
        "pandas>=2.1.0",
        "langdetect>=1.0.9",
        "pyyaml>=6.0.1",
        "click>=8.1.7",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.2",
            "black>=23.9.1",
            "flake8>=6.1.0",
            "mypy>=1.5.1",
            "isort>=5.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rag-cli=cli:cli",
        ],
    },
    python_requires=">=3.9",
    author="Your Name",
    author_email="your.email@example.com",
    description="Multilingual RAG system with Qdrant and LangChain",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
