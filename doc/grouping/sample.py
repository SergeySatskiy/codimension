
# cml 1 gb id=2 title=Imports
# cml 1 gb id=0 title="Standard imports"
from sys import exit
import os
# cml 1 ge id=0

# cml 1 gb id=1 title="Project imports"
import project_utils
import project_misc
# cml 1 ge id=1
# cml 1 ge id=2

base_path = os.path.curdir()
if project_utils.projectLoaded():
    base_path = project_utils.getBasePath()

