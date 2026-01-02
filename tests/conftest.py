import textwrap
import pytest

@pytest.fixture
def sample_md_with_header():
    return textwrap.dedent("""
    # How to cite

    Some intro text.

    ```{admonition} Note
    Use Vancouver style for journal articles.
    ```
    
    BibTeX:
    ```
    @article{castro2025,
      title = {Estimating gambling harms},
      author = {Castro Rivadeneira, Alvaro and Volberg, Rachel and Reich, Nicholas},
      year = {2025}
    }
    ```
    
    ```python
    # generic code fence should remain unchanged
    print("hello")
    ```
    """).strip()

@pytest.fixture
def sample_md_without_header():
    return textwrap.dedent("""
    Some intro text without H1.

    ```{admonition} Reminder
    Cite software and data separately.
    ```
    """).strip()

@pytest.fixture
def sample_md_mixed_blanklines():
    return "Line1\n\n\n\nLine2\n\n\nLine3\n"

@pytest.fixture
def sample_bibtex_already_fenced():
    return textwrap.dedent("""
    ```bibtex
    @article{key2024,
      title = {Title},
      author = {Author},
      year = {2024}
    }
    ```
    """).strip()

