import sys
from PptExample.Crawler import *


def main(args=None):
    # If no args are provided, it defaults to None

    if args is None:
        args = sys.argv[1:]
        # retrieves all arguments passed to the script from the command line (ignoring the script name)

    PttWebCrawler(args)

if __name__ == "__main__":
    # checks if the script is being executed directly (not imported as a module)
    # When a Python file is run, its __name__ variable is set to "__main__"

    main()