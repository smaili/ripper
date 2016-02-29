# -*- coding: utf-8 -*-
#------------------------------------------------------------------------
#
#     /$$$$$$$  /$$
#    | $$__  $$|__/
#    | $$  \ $$ /$$  /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$
#    | $$$$$$$/| $$ /$$__  $$ /$$__  $$ /$$__  $$ /$$__  $$
#    | $$__  $$| $$| $$  \ $$| $$  \ $$| $$$$$$$$| $$  \__/
#    | $$  \ $$| $$| $$  | $$| $$  | $$| $$_____/| $$
#    | $$  | $$| $$| $$$$$$$/| $$$$$$$/|  $$$$$$$| $$
#    |__/  |__/|__/| $$____/ | $$____/  \_______/|__/
#                  | $$      | $$
#                  | $$      | $$
#                  |__/      |__/
#
#     ripper.py
#     This is the main python file for scraping
#     and retrieving content from a website.
#
#   BeautifulSoup   http://www.crummy.com/software/BeautifulSoup/
#
#------------------------------------------------------------------------

# Imports
#------------------------------------------------------------------------
import bs4, config, os, re, socket, subprocess, sys, urllib2, time


# Statics
#------------------------------------------------------------------------
TAG_REGEX = re.compile(r'<[^>]+>')


# Functions
#------------------------------------------------------------------------
def _as_string(tag):
    return tag.string or TAG_REGEX.sub( '', str(tag) )

def _get(url):
    print "Getting URL " + url
    while True:
        try:
            if not url.startswith( 'http' ):
                if 'cgi-bin/' not in url:
                    url = '/cgi-bin/' + url
                # news.google.com/nwshp?hl=en
                url = 'http://www.findagrave.com/' + url.replace('//', '/') # just to be clean
            req = urllib2.Request( url, headers={ 'User-Agent': config.SCRAPE_UA } )
            return urllib2.urlopen( req , timeout=config.SCRAPE_TIMEOUT ).read()
        except:
            print "GET had an error with " + url
            time.sleep( config.SCRAPE_WAIT )
            print "Trying again..."


def _get_pic(url, path):
    dest = path + '/' + url.split('/')[-1]
    if not os.path.exists(dest):
        img = _get( url )
        with open( dest, 'w' ) as f:
            f.write(img)
        print "Saved image " + dest
    else:
        print "Don't need to save " + dest


def create_dir(name):
    if os.path.exists(name) and config.APP_OVERWRITE:
        subprocess.call(['rm', '-fr', name ])

    if not os.path.exists(name):
        os.mkdir(name)
        return True
    else:
        return False


def crawl(url):
    html = _get(url)
    if html:
        soup = bs4.BeautifulSoup(html, 'lxml')
        links = soup('a')

        for link in links:
            if link['href'].startswith( '/cgi-bin/fg.cgi?page=gr' ):
                print ""
                print "Getting grave " + link['href']
                data = {}
                grave = _get( link['href'] )
                if grave:
                    grave = bs4.BeautifulSoup(grave, 'lxml')
                    data['link'] = link['href']

                    # Name
                    bold = grave( 'font', { 'class' : 'plus2' } )[0].b
                    data['name'] = _as_string( bold ) # need to strip html if name.string is None
                    print "Parsing Memorial of " + data['name']
                    folder = config.APP_SAVE_PATH + '/' + data['name']
                    if create_dir( folder ):
                        # DOB, DOD, Buried/Cremated
                        print "Extracting Data"
                        tds = grave( 'td' )
                        for td in tds:
                            s = td.string or ''
                            if s.startswith('Birth'):
                                data['dob'] = td.nextSibling.contents[0]
                            elif s.startswith('Death'):
                                data['dod'] = td.nextSibling.contents[0]
                            elif _as_string( td ).startswith('Buri'):
                                place = td.contents[2]
                                data['buried'] = td.a.string if td.a else str( td )

                        for name in data:
                            with open( '%s/%s.txt' % ( folder, name ), 'w' ) as f:
                                f.write( data[name].encode('utf8') )
                        print "Extracting complete"


                        # Images
                        print "Fetching Images"
                        photos = bs4.BeautifulSoup( _get( grave( 'a', { 'title' : 'Click to View Photos' }  )[0]['href'] ), 'lxml' )
                        images = []

                        links = photos( 'a', { 'class' : re.compile('^thumb') } )
                        if links:
                            for link in links:
                                images.append( bs4.BeautifulSoup( _get( link['href'] ), 'lxml' )( 'img', { 'src' : re.compile('^http://image') } ) )
                        else:
                            images.append( photos( 'img', { 'src' : re.compile('^http://image') } ) )
                        
                        for image_set in images:
                            for img in image_set:
                                # make sure we don't re-encounter thumbnail links!
                                if img.parent.name != 'a' or img.parent['href'].startswith('http://image'):
                                    _get_pic( img['src'], folder )
                                    break
                        print "Fetching complete"

                    print "Parsing complete for " + data['name']
                    print ""


        # after getting all graves for this page, we move to the next
        # looking for -> <a href="***"><img src="/icons2/rightArrowTall.gif" border="0"></a>
        next_link = soup( 'img', { 'src' : '/icons2/rightArrowTall.gif' } )
        if next_link:
            crawl( next_link[0].parent['href'] )



def ripp():
    print ""
    print "Ripping memorials"
    print ""

    letters = config.SEARCH_LETTERS.replace('\n','').split()

    for letter in letters:
        print "Crawling letter %s" % letter
        print "------------------------------"
        print ""
        url = config.SCRAPE_URL % letter
        crawl(url)
        print "Crawling complete for letter %s" % letter
        print ""

    print "Ripping complete"
    print ""


# Main
#------------------------------------------------------------------------
if __name__=="__main__":
    try:
        sys.path.append(config.PY_HOME)

        ripp()

    except:
        print ""
        print "To use: python ripp.py"
        print ""