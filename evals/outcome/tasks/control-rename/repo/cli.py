"""Print the slug for a title: python3 cli.py "My Post Title" """
import sys

from textutil import slugify_title

if __name__ == "__main__":
    print(slugify_title(" ".join(sys.argv[1:])))
