#!/usr/bin/env python

try:
    from Levenshtein import distance as lev_dist
    from Levenshtein import ratio as lev_ratio
except Exception, e:
    print "Install this first:\n\t $ pip install python-levenshtein"
    exit(0)

import urlparse
import re
import argparse
import sys
 
def add_padd(input, pad_size=50, pad_char='X'):
    if isinstance(input, list):
        return [x.ljust(pad_size, pad_char) for x in input]
    return input.ljust(pad_size, pad_char)

class Cluster(object):
    def __init__(self, ):
        self.clusters = {'clusters': {}}
 
    def clustering(self, elems, threshold, netloc_w, path_w, qs_w):
        clusters = {}
        cid = 0
 
        for i, line in enumerate(elems):
            if i == 0:
                clusters[cid] = []
                clusters[cid].append(line)
            else:
                last = clusters[cid][-1]
                if url_distance(last, line, netloc_w=netloc_w, path_w=path_w, qs_w=qs_w) >= threshold:
                    clusters[cid].append(line)
                else:
                    cid += 1
                    clusters[cid] = []
                    clusters[cid].append(line)

        self.clusters['clusters'] = clusters
        self.clusters['clusters']['largest'] = self.get_largest_cluster()
        self.clusters['clusters']['number_of_clusters'] = cid + 1
 
    def get_largest_cluster(self):
        clusters = self.clusters['clusters']
 
        maxi_k = None
        maxi_v = None
        first = True
        for k,v in clusters.iteritems():
            if first:
                maxi_k = k
                maxi_v = len(v)
                first = False
            else:
                if len(v) > maxi_v:
                    maxi_v = len(v)
                    maxi_k = k
        
        return clusters[maxi_k]
 
#############################################################################

class URL:
    def __init__(self, raw_url):
        self.raw_url = raw_url
        self.parsed_url = urlparse.urlparse(self.raw_url)
        self.tokens = {}
        self._make_tokens()

    def __repr__(self):
        return self.raw_url  

    def _make_pattern_tokens(self, item):
        def makepattern(elem):
            if elem not in ['/', '.', '&', '=', '?', '#', '-', ':']:
                return '*'
            return elem 

        return ''.join(map(makepattern, item))

    def _make_netloc_tokens(self, netloc):
        t = [self._make_pattern_tokens(netloc)]
        for e in re.split(r"\.|\-|_", netloc):
            t.append(e)
        return t

    def _make_path_tokens(self, path):
        return [t for t in re.split(r"\/|\-|\.", path)]

    def _make_querystring_tokens(self, qs):
        t = []
        for i in qs.split('&'):
            t.append(i)
            for j in qs.split('='):
                t.append(j)
        return t

    def _make_fragment_tokens(self, fragment):
        return [t for t in re.split(r"\/|\.|\&|=|\?|#|-|_|:", fragment)]

    def _make_tokens(self):
        self.tokens['pattern']  = add_padd([self._make_pattern_tokens(self.raw_url)])
        self.tokens['netloc']   = add_padd(self._make_netloc_tokens(self.parsed_url.scheme + '://' + self.parsed_url.netloc))
        self.tokens['path']     = add_padd(self._make_path_tokens(self.parsed_url.path))
        self.tokens['querystring'] = add_padd(self._make_querystring_tokens(self.parsed_url.query))
        self.tokens['fragment'] =   add_padd(self._make_fragment_tokens(self.parsed_url.fragment))


#############################################################################

MIN_SCORE = MAX_SCORE = AVG_SCORE = None

def url_distance(url1, url2, pattern_w=1, netloc_w=1, path_w=1, qs_w=1):   
    global MIN_SCORE
    global MAX_SCORE
    global AVG_SCORE 
    
    score = 0.0

    # Pattern
    score += lev_ratio(url1.tokens['pattern'][0], url2.tokens['pattern'][0]) * pattern_w

    # Netloc
    netloc_score = 0
    biggest, smallest = (url1, url2) if len(url1.tokens['netloc']) >= len(url2.tokens['netloc']) else (url2, url1)
    for i, v in enumerate(biggest.tokens['netloc']):
        try:
            netloc_score += lev_ratio(v[50:], smallest.tokens['netloc'][i][50:])
        except IndexError, e:
            pass
    score += netloc_score * netloc_w

    # Path
    path_score = 0
    biggest, smallest = (url1, url2) if len(url1.tokens['path']) >= len(url2.tokens['path']) else (url2, url1)
    for i, v in enumerate(biggest.tokens['path']):
        try:
            path_score += lev_ratio(v[50:], smallest.tokens['path'][i][50:])
        except IndexError, e:
            pass
    score += path_score * path_w

    # QueryString 
    # Merge the two lists removing duplicates, if the resulting len is the same as max_len
    #  then original lists are equals
    qs_score = 0.0
    longest, shortest = (url1, url2) if len(url1.tokens['querystring']) > len(url2.tokens['querystring']) else (url2, url1) # To preserve commutativity
    max_len = len(longest.tokens['querystring'])
    qs_score += float(max_len) / len(list(set(url1.tokens['querystring'] + url2.tokens['querystring'])))

    # Brutal, do compare every token with every other token
    avg_s = 1.0
    for e1 in url1.tokens['querystring']:
        for e2 in url2.tokens['querystring']:
            avg_s += lev_ratio(e1[50:], e2[50:])
            avg_s = avg_s / 2

    qs_score += avg_s
    score += qs_score * qs_w


    # Calculate
    if (score < MIN_SCORE) or (MIN_SCORE is None):
        MIN_SCORE = score
    if score > MAX_SCORE or (MAX_SCORE is None):
        MAX_SCORE = score
    if AVG_SCORE is None:
        AVG_SCORE = score
    else:
        AVG_SCORE = (AVG_SCORE + score) / 2

    return score

#############################################################################
 
if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description='''A quick and rude url clusterer!\n
Each url is compared to each other by computing a score index: the bigger 
the score the bigger the similarities. The threshold is the minimun score 
value that two url must have to be grouped together. It's possible to alter 
the score calculation by assigning more prominence to given url components 
(namely the netloc, path or the query string).''',
        epilog='Example clustering with threshold 5 and more focus on query string:\n  $ cat url_list | urlcluster.py -t 5 -qsw 1.5\n',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('-t', '--threshold', nargs='?', required=True, dest='threshold', type=float,
        help='Threshold value on which score between elements is compared to decide clusters.')
    p.add_argument('-nw', '--netloc-weight', nargs='?', dest='nw', default='1.0', type=float,
        help='NETLOC weight, used to calcuate netloc importance.')
    p.add_argument('-pw', '--path-weight', nargs='?', dest='pw', default='1.0', type=float,
        help='PATH weight, used to calcuate url path importance.')
    p.add_argument('-qsw', '--querystring-weight', nargs='?', dest='qsw', default='1.0', type=float,
        help='QUERYSTRING weight, used to calcuate query string importance.')
    p.add_argument('-no', '--no-output', dest='no', action='store_true',
        help='Suppress informational output, print just one element per line and divide every cluster with a blank line. Useful for fast grepping/awking.')
    p.add_argument('filename', type=argparse.FileType('r'), nargs='?', default='-', help='File name, containing one URL per line')
    args = p.parse_args()


    urllist =[]
    for line in args.filename:
        if line != '':
            urllist.append(URL(line.rstrip()))
    
    cl = Cluster()
    cl.clustering(urllist, 
        threshold=float(args.threshold),
        netloc_w=args.nw,
        path_w=args.pw,
        qs_w=args.qsw)

    # Printing time!
    if not args.no:
        print "[i] Thresholds:"
        print " |-- Chosen: %s" % args.threshold
        print " |-- [+] Computed Thresholds"
        print " |    |-- MIN: %s" % MIN_SCORE
        print " |    |-- MAX: %s" % MAX_SCORE
        print " |    |-- AVG: %s" % AVG_SCORE
        print " | "
        print "[i] Weights:"
        print " |-- Netloc: %s" % args.nw
        print " |-- Path: %s" % args.pw
        print " |-- Query String: %s" % args.qsw
        print " | "
        print "[i] Number of Clusters: %s\n" % cl.clusters['clusters']['number_of_clusters']

    for c in xrange(cl.clusters['clusters']['number_of_clusters']):
        if not args.no:
            print"[+] Cluster #%d" % c
        for elem in cl.clusters['clusters'][c]:
            print elem
        print ''