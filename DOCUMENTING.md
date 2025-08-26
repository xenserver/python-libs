# Documenting using Sphinx

This project uses **Google style docstrings** for Python code documentation. These docstrings are compatible with Sphinx (with the `sphinx.ext.napoleon` extension) and other documentation tools.

## Why Google Style Docstrings?

- Clear, readable format
- Widely supported by documentation generators
- Easy to maintain

## Example Google Style Docstring

```python
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a (int): First integer.
        b (int): Second integer.

    Returns:
        int: The sum of `a` and `b`.

    Raises:
        ValueError: If either argument is not an integer.
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("Arguments must be integers.")
    return a + b
```

## Steps to Document Your Code

1. **Write Google style docstrings** for all public modules, classes, and functions.
2. **Include sections** such as `Args`, `Returns`, `Raises`, and `Examples` as needed.
3. **Keep docstrings concise and informative.**

## Benefits of using Sphinx

- Supports docstring formats – such as Google-style, NumPy-style, and reST.
- Autodoc extension – can automatically extract documentation from Python docstrings.
- Integration with Read the Docs – makes it easy to publish and host documentation online.
- Theme support – like Read the Docs theme or the modern Furo theme.

## Building the documentation

```bash
pip install -r docs/requirements.txt
make -C docs html
```

Open `docs/html/index.html` in a web browser.

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Sphinx Napoleon Documentation](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
