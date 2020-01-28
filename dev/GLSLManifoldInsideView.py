from __future__ import print_function
import sys

darwinTkMsg = """
On some versions of Mac OS X and Tk, it might be necessary to run the
following command to make the WASD navigation keys work properly:

    defaults write -g ApplePressAndHoldEnabled -bool false

The effect (disabling the ability to enter accented characters by, e.g.,
holding the e key) can be undone with:

    defaults write -g ApplePressAndHoldEnabled -bool true
"""

"""
An attempt at fixing the navigation keys (using pyobjc installed with pip):

    from Foundation import NSUserDefaults

    NSUserDefaults.standardUserDefaults().setBool_forKey_(False, 'ApplePressAndHoldEnabled')
    print(NSUserDefaults.standardUserDefaults().get('ApplePressAndHoldEnabled'))

"""

from raytracing.raytracing_widget import *
from snappy import Manifold

def run_perf_test(): 
    gui = RaytracingWidget(Manifold("m004"))

    PerfTest(gui.main_widget)

def main(manifold):
    if sys.platform == 'darwin':
        print(darwinTkMsg)

    gui = RaytracingWidget(manifold)
    gui.main_widget.focus_set()
    gui.container.mainloop()
    
if __name__ == '__main__':
    print(sys.argv)

    if sys.argv[1] == 'perf':
        run_perf_test()
    else:
        main(Manifold(sys.argv[1]))
