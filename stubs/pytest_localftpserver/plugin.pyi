from .helper_functions import get_scope as get_scope
from .servers import PytestLocalFTPServer as PytestLocalFTPServer
from _typeshed import Incomplete

FIXTURE_SCOPE: Incomplete

def ftpserver(request): ...
def ftpserver_TLS(request): ...
