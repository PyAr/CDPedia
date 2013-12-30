#!//usr/bin/env python

import os
import sys
import time

URL_LIST = (
    "http://dumps.wikimedia.org/eswiki/latest/"
    "eswiki-latest-all-titles-in-ns0.gz"
)
ART_LIST = "eswiki-latest-all-titles-in-ns0"
ART_NAMESP = "articles_by_namespaces.txt"
ART_INCLUDE = "utilities/include.txt"
ART_ALL = "all_articles.txt"


def show(t, *args):
    print "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), t % args)
    sys.stdout.flush()


def get_lists(branch_dir):
    """Get the list of wikipedia articles."""
    show("Getting list file")
    # FIXME: convert these two lines to a standard Python code
    os.system("wget -c %s" % URL_LIST)
    os.system("gunzip -f %s.gz" % ART_LIST)
    fh_artall = open(ART_ALL, "wb")
    with open(ART_LIST) as fh:
        q = 0
        for lin in fh:
            q += 1
            fh_artall.write(lin)
    tot = q
    show("Downloaded %d general articles", q)

    show("Getting the articles from namespaces")
    import list_articles_by_namespaces
    list_articles_by_namespaces.main()
    with open(ART_NAMESP) as fh:
        q = 0
        for lin in fh:
            q += 1
            fh_artall.write(lin)
    tot += q
    show("Downloaded %d namespace articles", q)

    with open(os.path.join(branch_dir, ART_INCLUDE)) as fh:
        q = 0
        for lin in fh:
            q += 1
            fh_artall.write(lin)
    tot += q
    show("Have %d articles in the include", q)

    fh_artall.close()
    show("Total of articles: %d", tot)


def scrap(branch_dir, dump_dir):
    """Get the pages from wikipedia."""
    show("Let's scrap")
    assert os.getcwd() == dump_dir
    res = os.system("python %s/utilities/scraper.py %s articulos" % (
        branch_dir, ART_ALL))
    print "======== result scrap", res


def main(branch_dir, dump_dir, nolists, noscrap):
    """Main entry point."""
    print "Branch directory:", repr(branch_dir)
    print "Dump directory:", repr(dump_dir)
    os.chdir(dump_dir)

    if not nolists:
        get_lists(branch_dir)

    if not noscrap:
        scrap(branch_dir, dump_dir)


if __name__ == "__main__":
    nolists = noscrap = False
    if "--no-lists" in sys.argv:
        sys.argv.remove("--no-lists")
        nolists = True
    if "--no-scrap" in sys.argv:
        sys.argv.remove("--no-scrap")
        noscrap = True

    if len(sys.argv) != 3:
        print "Usage: %s [--no-lists] [--no-scrap] <branch_dir> <dump_dir>" % (
            sys.argv[0],)
        exit()

    branch_dir = os.path.abspath(sys.argv[1])
    dump_dir = os.path.abspath(sys.argv[2])

    # branch dir must exist
    if not os.path.exists(branch_dir):
        print "The branch dir doesn't exist!"
        exit()
    utils_dir = os.path.join(branch_dir, "utilities")
    sys.path.insert(1, utils_dir)

    # dump dir may not exist, let's just create if it doesn't
    if not os.path.exists(dump_dir):
        os.mkdir(dump_dir)

    main(branch_dir, dump_dir, nolists=nolists, noscrap=noscrap)
