import textwrap
import pytest

@pytest.fixture
def sample_defs_md():
    return textwrap.dedent("""
    # Terminology

    (model-tasks)=
    ## Modeling Tasks Terminology
    [Learn more about modeling tasks](somewhere)

    (prediction-terms)=
    ## Prediction Terminology
    ```{figure}
    name: horizon-nomenclature
    ```

    (def-nowcast)=
    A short-term estimate (#def-model-output).

    A future prediction.
    """).strip()


@pytest.fixture
def sample_abbr_md():
    return textwrap.dedent("""
    **CDC**
    : Centers for Disease Control and Prevention

    **WHO**
    : World Health Organization
    """).strip()


@pytest.fixture
def sample_md_with_header():
    """Markdown containing H1, admonition, BibTeX block, and generic code fence."""
    return (
        textwrap.dedent(
            """
            # How to cite

            Some intro text.

            ```{{admonition}} Note
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
            """
        ).strip()
    )


@pytest.fixture
def sample_md_without_header():
    """Markdown without top-level header but with an admonition."""
    return (
        textwrap.dedent(
            """
            Some intro text without H1.

            ```{{admonition}} Reminder
            Cite software and data separately.
            ```
            """
        ).strip()
    )


@pytest.fixture
def sample_md_mixed_blanklines():
    """Markdown with excessive blank lines."""
    return "Line1\n\n\n\nLine2\n\n\nLine3\n"


@pytest.fixture
def sample_bibtex_already_fenced():
    """Markdown containing a correctly fenced BibTeX block."""
    return (
        textwrap.dedent(
            """
            ```bibtex
            @article{key2024,
              title = {Title},
              author = {Author},
              year = {2024}
            }
            ```
            """
        ).strip()
    )

