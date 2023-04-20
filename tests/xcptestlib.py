import locale

# We might be called with the locale not set, in which case python2's default
# charset is ASCII. This happens when code is running as an xapi-plugin.
# In this case any decode() calls added for Python3, which could (wrongly)
# be also used when running in Python2, at least have to use encoding="utf-8",
# or they will raise Exceptions. Test this worst-case scenario.
# For reference, see the explanations here:
# https://stackoverflow.com/questions/40029017/python2-using-decode-with-errors-replace-still-returns-errors
def set_c_locale():
    """
    Disable any UTF-8 locale setting to ensure that when decode() gets
    non-ASCII data do decode, it has the arg encoding="utf-8", otherwise
    it would raise UnicodeDecodeError which would abort the calling program.
    Likewise, this can catch wrong uses of encode(**args) on strings which would
    trigger the sequence of string.decode().encode(**args) internally, likwise
    raising UnicodeDecodeError in the .decode() step:
    """
    locale.setlocale(locale.LC_ALL, 'C')
